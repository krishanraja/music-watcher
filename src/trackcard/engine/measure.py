"""Audio in, a trackcard card out, into the worker's cache (outside the clone).

The audio is always renamed to `<version id>.wav` first, so the card's `file` field and header never carry a Drive file
name. Stems are tried first; on a failure or a timeout the card is measured again without stems, and the card says so.
Audio is deleted in `finally`. Failures come back as codes (privacy.WHY), never as stderr.
"""
from __future__ import annotations

import html
import importlib.util
import json
import re
import subprocess
import urllib.request
from pathlib import Path

from .config import Config

LENGTH_TOLERANCE_S = 6
PREVIEW_UA = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def to_wav(cfg: Config, src: Path, wav: Path) -> bool:
    if src.suffix.lower() in (".wav", ".wave"):
        if src != wav:
            src.rename(wav)
        return True
    r = _run([*cfg.tool("ffmpeg"), "-y", "-loglevel", "error", "-i", str(src), "-ar", "44100", "-ac", "2", str(wav)], 900)
    return bool(r and r.returncode == 0 and wav.exists())


def analyze(cfg: Config, wav: Path, out: Path, bpm: float | None = None, key: str | None = None) -> tuple[dict | None, str]:
    """Run trackcard on wav into out/. Returns (card, "") or (None, why-code). Leaves the wav for the caller to delete."""
    out.mkdir(parents=True, exist_ok=True)
    extra = (["--bpm", str(bpm)] if bpm else []) + (["--key", str(key)] if key else [])
    base = [*cfg.tool("trackcard"), "analyze", str(wav), "--json", "--sections", "laplacian", "--out", str(out), *extra]
    card_path = out / f"{wav.stem}.trackcard.json"
    r = _run(base, 3600)
    why = "trackcard_failed_stems" if r is not None else "timeout"
    if r is None or r.returncode != 0 or not card_path.exists():
        r = _run([*base, "--no-stems"], 1800)
        if r is None:
            return None, "timeout"
        if r.returncode != 0 or not card_path.exists():
            return None, "trackcard_failed_no_stems"
    try:
        return json.loads(card_path.read_text(encoding="utf-8")), ""
    except (OSError, json.JSONDecodeError):
        return None, why


def measure_file(cfg: Config, src: Path, vid: str, out: Path, bpm=None, key=None) -> tuple[dict | None, str]:
    """src: a downloaded audio file in the work dir. Always deletes it and its WAV."""
    wav = cfg.work_dir / f"{vid}.wav"
    try:
        if not to_wav(cfg, src, wav):
            return None, "convert_failed"
        return analyze(cfg, wav, out, bpm, key)
    finally:
        for f in (src, wav):
            f.unlink(missing_ok=True)


# ---------------------------------------------------------------- links (Stage B: references)

TRACK_RE = re.compile(r"open\.spotify\.com/(?:intl-[a-z]{2}(?:-[a-z]{2})?/)?track/([A-Za-z0-9]{22})")
PLAYLIST_RE = re.compile(r"open\.spotify\.com/(?:intl-[a-z]{2}(?:-[a-z]{2})?/)?(playlist|album|artist|episode|show)/")


def track_id(url: str) -> str | None:
    m = TRACK_RE.search(url)
    return m.group(1) if m else None


def track_url(tid: str) -> str:
    return f"https://open.spotify.com/track/{tid}"


def spotify_meta(tid: str) -> dict:
    """Title, artists and length from Spotify's link-preview tags (the same route as taste/inspo/watch.py)."""
    req = urllib.request.Request(track_url(tid), headers={"User-Agent": PREVIEW_UA, "Accept-Language": "en"})
    page = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")

    def meta(name: str) -> str | None:
        m = re.search(r'<meta[^>]+(?:property|name)="' + re.escape(name) + r'"[^>]+content="([^"]*)"', page)
        return html.unescape(m.group(1)) if m else None

    desc = meta("og:description") or ""
    duration = meta("music:duration")
    return {"title": meta("og:title"), "artists": desc.split(" · ")[0] if " · " in desc else None,
            "duration_s": int(duration) if duration and duration.isdigit() else None}


def soundcloud_match(cfg: Config, artists: str, title: str, want_s: int) -> str | None:
    r = _run([*cfg.tool("ytdlp"), "--dump-json", "--flat-playlist", "--no-warnings", f"scsearch5:{artists} {title}"], 180)
    best = None
    for line in (r.stdout if r else "").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        d = e.get("duration")
        url = e.get("url") or e.get("webpage_url") or ""
        if d is None or "/s-" in url:
            continue
        gap = abs(float(d) - want_s)
        if gap <= LENGTH_TOLERANCE_S and (best is None or gap < best[0]):
            best = (gap, url)
    return best[1] if best else None


def fetch_audio(cfg: Config, url: str, stem: Path) -> Path | None:
    r = _run([*cfg.tool("ytdlp"), "-x", "--audio-format", "wav", "--no-playlist", "--no-warnings",
              "-o", f"{stem}.%(ext)s", url], 1800)
    wav = stem.with_suffix(".wav")
    return wav if r and r.returncode == 0 and wav.exists() else None


# ---------------------------------------------------------------- brain feed rows

def graph_module(clone: Path):
    """taste/graph/build_graph.py from the same checkout, so the feed and the graphs share one definition."""
    spec = importlib.util.spec_from_file_location("build_graph", clone / "taste" / "graph" / "build_graph.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def feed_row(clone: Path, card: dict, tid: str, title: str, artists: str, spotify_s: int, measured_from: str) -> dict:
    bg = graph_module(clone)
    row = {"id": tid, "title": title, "artists": artists, "duration_s": spotify_s, "measured": True,
           "measured_from": measured_from, **bg.features(card, spotify_s)}
    if card.get("stems_available"):
        row.update(bg.stem_features(card))
    return row
