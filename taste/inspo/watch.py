"""Music Inspo watcher: turn each NEW drop in Krish's Drive "Music Inspo" folder into a measured track card.

Runs unattended on the worker (a systemd timer). One pass:

  1. List the Drive folder (rclone, read-only). A drop is new when its Drive id + checksum is not in the state file.
  2. Turn each new drop into audio:
       - an audio file (wav, mp3, flac, m4a, aiff, ogg) is downloaded as is;
       - a text file or Google Doc is read for links:
           Spotify track  -> title, artist and length from the track page, then a SoundCloud recording whose real
                             length is within 6 s of Spotify's (the same rule as taste/graph, against wrong uploads);
           SoundCloud     -> that recording;
           YouTube        -> left for a home computer (YouTube refuses datacenter machines), recorded as such.
  3. Measure it with trackcard (full track, Laplacian sections, with Demucs stems; without stems if they fail).
  4. Write taste/inspo/cards/<key>.trackcard.json + .md, a row in taste/inspo/index.csv and a line in
     taste/inspo/fetch_log.jsonl, commit them to the rolling branch `inspo/new-drops`, push, and keep one PR open.
  5. Delete the audio (never commit audio). Mark the drop done only after the push, so a failed run retries.

It never writes to Drive. Settings come from the environment (the worker's unit):
  MUSIC_INSPO_FOLDER_ID   Drive folder id (required; kept out of this repository)
  RCLONE_REMOTE           rclone remote name (default gdrive)
  INSPO_REPO              a checkout of this repository the job may commit in (required)
  INSPO_STATE             state file (default ~/.music-watcher/inspo-state.json)
  INSPO_WORK              scratch folder for audio (default ~/media/inspo)
  YTDLP, TRACKCARD        tool paths (default: on PATH)
  INSPO_MAX_PER_RUN       drops per pass (default 3)
"""
from __future__ import annotations

import csv
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

AUDIO_EXT = {".wav", ".mp3", ".flac", ".m4a", ".aif", ".aiff", ".ogg", ".opus"}
TEXT_MIME = ("text/", "application/vnd.google-apps.document", "application/vnd.google-apps.shortcut")
LENGTH_TOLERANCE_S = 6
BRANCH = "inspo/new-drops"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0 Safari/537.36"
INDEX_FIELDS = ["key", "added_at", "title", "artists", "source", "link", "measured_from", "audio_source",
                "duration_s", "bpm", "bpm_confidence", "key_name", "camelot", "key_confidence",
                "integrated_lufs", "drops", "stems", "card"]

env = os.environ.get
FOLDER = env("MUSIC_INSPO_FOLDER_ID")
REMOTE = env("RCLONE_REMOTE", "gdrive")
REPO = Path(env("INSPO_REPO", "")).expanduser()
STATE = Path(env("INSPO_STATE", "~/.music-watcher/inspo-state.json")).expanduser()
WORK = Path(env("INSPO_WORK", "~/media/inspo")).expanduser()
YTDLP = env("YTDLP", "yt-dlp")
TRACKCARD = env("TRACKCARD", "trackcard")
MAX_PER_RUN = int(env("INSPO_MAX_PER_RUN", "3"))


def log(msg: str) -> None:
    print(dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%SZ ") + msg, flush=True)


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def rclone(*args: str, timeout: int = 600) -> subprocess.CompletedProcess:
    return run(["rclone", *args, f"--drive-root-folder-id={FOLDER}"], timeout=timeout)


# ---------- Drive ----------

def list_drops() -> list[dict]:
    # Export formats here too, so a Google Doc is listed (and later read) as "<name>.txt", not "<name>.docx".
    r = rclone("lsjson", f"{REMOTE}:", "--files-only", "--max-depth", "1", "--hash", "--drive-export-formats", "txt")
    if r.returncode != 0:
        raise SystemExit("rclone lsjson failed: " + r.stderr.strip()[-300:])
    return json.loads(r.stdout or "[]")


def drop_text(item: dict) -> str:
    r = rclone("cat", f"{REMOTE}:{item['Path']}", "--drive-export-formats", "txt", timeout=120)
    return r.stdout if r.returncode == 0 else ""


def download(item: dict, dest: Path) -> bool:
    r = rclone("copyto", f"{REMOTE}:{item['Path']}", str(dest))
    return r.returncode == 0 and dest.exists()


# ---------- links ----------

PREVIEW_UA = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"


def spotify_meta(track_id: str) -> dict:
    # Browsers get Spotify's JavaScript app with no metadata; link-preview crawlers get server-rendered Open Graph
    # tags, including music:duration (checked 2026-11-14: "Need You" -> 201 s, as in taste/graph/tracks.csv).
    # Accept-Language: Spotify localises by the caller's location (the worker got an Arabic comma between artists).
    req = urllib.request.Request(f"https://open.spotify.com/track/{track_id}",
                                 headers={"User-Agent": PREVIEW_UA, "Accept-Language": "en"})
    page = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")

    def meta(name: str) -> str | None:
        m = re.search(r'<meta[^>]+(?:property|name)="' + re.escape(name) + r'"[^>]+content="([^"]*)"', page)
        return html.unescape(m.group(1)) if m else None

    desc = meta("og:description") or ""          # "Artist · Album · Song · 2018"
    duration = meta("music:duration")
    return {"title": meta("og:title"), "artists": desc.split(" · ")[0] if " · " in desc else None,
            "duration_s": int(duration) if duration and duration.isdigit() else None}


def soundcloud_match(artists: str, title: str, want_s: int) -> dict | None:
    r = run([YTDLP, "--dump-json", "--flat-playlist", "--no-warnings", f"scsearch5:{artists} {title}"], timeout=180)
    best = None
    for line in r.stdout.splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        d = e.get("duration")
        if d is None:
            continue
        gap = abs(float(d) - want_s)
        if gap <= LENGTH_TOLERANCE_S and (best is None or gap < best["gap"]):
            best = {"url": e.get("url") or e.get("webpage_url"), "title": e.get("title"), "gap": round(gap, 1)}
    return best


def fetch_audio(url: str, stem: Path) -> Path | None:
    r = run([YTDLP, "-x", "--audio-format", "wav", "--no-playlist", "--no-warnings", "-o", f"{stem}.%(ext)s", url])
    wav = stem.with_suffix(".wav")
    return wav if r.returncode == 0 and wav.exists() else None


def to_wav(src: Path) -> Path | None:
    if src.suffix.lower() == ".wav":
        return src
    wav = src.with_suffix(".wav")
    r = run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ar", "44100", "-ac", "2", str(wav)])
    return wav if r.returncode == 0 and wav.exists() else None


# ---------- one drop ----------

def process(item: dict) -> dict:
    """Return a result: status in {measured, left_for_home, no_match, skipped, failed} + fields."""
    WORK.mkdir(parents=True, exist_ok=True)
    added = item.get("ModTime", "")[:19] + "Z"
    name, mime = item["Name"], item.get("MimeType", "")
    base = {"added_at": added, "drive_name": name}
    ext = Path(name).suffix.lower()

    if ext in AUDIO_EXT or mime.startswith("audio/"):
        key = "drive-" + item["ID"]
        src = WORK / f"{key}{ext or '.audio'}"
        if not download(item, src):
            return {**base, "status": "failed", "why": "download failed", "key": key}
        wav = to_wav(src)
        return measure({**base, "key": key, "title": Path(name).stem, "artists": "", "source": "audio file",
                        "link": "", "audio_source": "dropped file", "measured_from": "full (dropped file)"}, wav, [src])

    if mime.startswith(TEXT_MIME) or ext in {".txt", ".url", ".webloc", ".md"} or name.startswith("http"):
        text = drop_text(item) + " " + name
        urls = re.findall(r"https?://[^\s\"'<>]+", text)
        sp = next((u for u in urls if "open.spotify.com/track/" in u), None)
        sc = next((u for u in urls if "soundcloud.com/" in u), None)
        yt = next((u for u in urls if re.search(r"youtube\.com|youtu\.be", u)), None)
        if sp:
            tid = re.search(r"/track/([A-Za-z0-9]+)", sp).group(1)
            m = spotify_meta(tid)
            rec = {**base, "key": tid, "title": m["title"] or "", "artists": m["artists"] or "", "source": "spotify",
                   "link": f"https://open.spotify.com/track/{tid}", "spotify_duration_s": m["duration_s"]}
            if not (m["title"] and m["duration_s"]):
                return {**rec, "status": "failed", "why": "Spotify page gave no title or length"}
            hit = soundcloud_match(rec["artists"], rec["title"], m["duration_s"])
            if not hit:
                return {**rec, "status": "left_for_home",
                        "why": f"no SoundCloud recording within {LENGTH_TOLERANCE_S} s of Spotify's length; "
                               "YouTube refuses the worker, so a home computer must fetch it"}
            wav = fetch_audio(hit["url"], WORK / tid)
            return measure({**rec, "audio_source": f"soundcloud: {hit['url']} (length gap {hit['gap']} s)",
                            "measured_from": "full (SoundCloud, length within 6 s of Spotify's)"}, wav, [])
        if sc:
            key = "sc-" + re.sub(r"[^A-Za-z0-9]+", "-", sc.split("soundcloud.com/")[1])[:60].strip("-")
            wav = fetch_audio(sc, WORK / key)
            return measure({**base, "key": key, "title": "", "artists": "", "source": "soundcloud", "link": sc,
                            "audio_source": f"soundcloud: {sc}", "measured_from": "full (SoundCloud link)"}, wav, [])
        if yt:
            return {**base, "key": "yt-" + item["ID"], "status": "left_for_home", "source": "youtube", "link": yt,
                    "why": "YouTube refuses datacenter machines; a home computer must fetch it"}
        return {**base, "key": "drive-" + item["ID"], "status": "skipped", "why": "no Spotify, SoundCloud or YouTube link"}

    return {**base, "key": "drive-" + item["ID"], "status": "skipped", "why": f"not audio or a link ({mime or ext})"}


def measure(rec: dict, wav: Path | None, extra_files: list[Path]) -> dict:
    if wav is None:
        return {**rec, "status": "failed", "why": "no audio to measure"}
    cards = REPO / "taste" / "inspo" / "cards"
    cards.mkdir(parents=True, exist_ok=True)
    named = wav.with_name(rec["key"] + ".wav")
    if wav != named:
        wav.rename(named)
    stems = True
    r = run([TRACKCARD, "analyze", str(named), "--json", "--sections", "laplacian", "--out", str(cards)], timeout=3600)
    if r.returncode != 0:  # Demucs out of memory or similar: keep the card, without stems, and say so
        stems = False
        r = run([TRACKCARD, "analyze", str(named), "--json", "--no-stems", "--sections", "laplacian",
                 "--out", str(cards)], timeout=1800)
    for f in [named, *extra_files]:
        f.unlink(missing_ok=True)
    card_path = cards / f"{rec['key']}.trackcard.json"
    if r.returncode != 0 or not card_path.exists():
        return {**rec, "status": "failed", "why": "trackcard failed: " + (r.stderr.strip()[-200:] or "no card")}
    c = json.loads(card_path.read_text())
    spot = rec.get("spotify_duration_s")
    if spot and abs(c["duration"] - spot) > LENGTH_TOLERANCE_S:
        rec["measured_from"] = f"partial: audio is {c['duration']:.0f} s, Spotify says {spot} s"
    return {**rec, "status": "measured", "stems": stems and c.get("stems_available", False),
            "duration_s": round(c["duration"], 1), "bpm": c.get("bpm"), "bpm_confidence": c.get("bpm_confidence"),
            "key_name": c.get("key"), "camelot": c.get("camelot"), "key_confidence": c.get("key_confidence"),
            "integrated_lufs": (c.get("loudness") or {}).get("integrated_lufs"), "drops": len(c.get("drops") or []),
            "card": f"cards/{rec['key']}.trackcard.json"}


# ---------- repository ----------

def git(*args: str) -> subprocess.CompletedProcess:
    return run(["git", *args], cwd=REPO, timeout=300)


def open_pr_count() -> int:
    out = run(["gh", "pr", "list", "--head", BRANCH, "--state", "open", "--json", "number", "--jq", "length"],
              cwd=REPO).stdout.strip()
    return int(out) if out.isdigit() else 0


def prepare_branch() -> None:
    """Keep adding to the open PR's branch; once it is merged (or closed), start again from main."""
    git("fetch", "-q", "origin")
    has_remote = git("ls-remote", "--exit-code", "--heads", "origin", BRANCH).returncode == 0
    base = f"origin/{BRANCH}" if (has_remote and open_pr_count() > 0) else "origin/main"
    git("checkout", "-q", "-B", BRANCH, base)


def record(results: list[dict]) -> None:
    inspo = REPO / "taste" / "inspo"
    inspo.mkdir(parents=True, exist_ok=True)
    index = inspo / "index.csv"
    new = not index.exists()
    with index.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=INDEX_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        for r in results:
            if r["status"] == "measured":
                w.writerow(r)
    with (inspo / "fetch_log.jsonl").open("a") as fh:
        for r in results:
            fh.write(json.dumps({k: v for k, v in r.items() if k != "spotify_duration_s"} | {
                "logged_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}) + "\n")


def publish(results: list[dict]) -> bool:
    git("add", "taste/inspo")
    if git("diff", "--cached", "--quiet").returncode == 0:
        return True
    measured = sum(r["status"] == "measured" for r in results)
    msg = (f"taste(inspo): {measured} new Music Inspo track(s) measured\n\n"
           + "\n".join(f"- {r['status']}: {r.get('artists') or ''} {r.get('title') or r.get('drive_name')}".rstrip()
                       for r in results)
           + "\n\nWritten by taste/inspo/watch.py on the worker.\n")
    # --force: the branch is this job's own; after a merge it restarts from main and must replace the old one.
    if git("commit", "-q", "-m", msg).returncode != 0 or \
            git("push", "-q", "--force", "-u", "origin", BRANCH).returncode != 0:
        return False
    if open_pr_count() == 0:
        body = ("New drops from the Drive **Music Inspo** folder, measured by `taste/inspo/watch.py` on the worker. "
                "This PR keeps collecting new cards until it is merged; then the next drop starts a fresh one. "
                "Each row in `taste/inspo/index.csv` says where its audio came from (`audio_source`, `measured_from`); "
                "`fetch_log.jsonl` also lists drops that were left for a home computer or skipped, and why.\n\n"
                "🤖 Generated by the worker's Music Inspo watcher")
        run(["gh", "pr", "create", "--base", "main", "--head", BRANCH,
             "--title", "taste(inspo): new Music Inspo drops measured", "--body", body], cwd=REPO)
    return True


# ---------- main ----------

def main() -> int:
    if not FOLDER or not REPO.is_dir():
        print("MUSIC_INSPO_FOLDER_ID and INSPO_REPO are required", file=sys.stderr)
        return 2
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    drops = list_drops()

    def sig(it: dict) -> str:
        return (it.get("Hashes") or {}).get("md5") or f"{it.get('Size')}@{it.get('ModTime')}"

    new = [it for it in drops if state.get(it["ID"], {}).get("sig") != sig(it)]
    new.sort(key=lambda it: it.get("ModTime", ""))
    log(f"{len(drops)} drops in the folder, {len(new)} new")
    if not new:
        return 0
    prepare_branch()
    results = []
    for it in new[:MAX_PER_RUN]:
        log(f"drop: {it['Name']} ({it.get('MimeType', '')})")
        try:
            res = process(it)
        except Exception as exc:  # noqa: BLE001 - one bad drop must not stop the pass
            res = {"key": "drive-" + it["ID"], "drive_name": it["Name"], "status": "failed", "why": repr(exc)[:200]}
        log(f"  -> {res['status']}" + (f": {res.get('why')}" if res.get("why") else ""))
        results.append(res)
    record(results)
    if not publish(results):
        log("commit/push failed; drops stay new and are retried next pass")
        return 1
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for it, res in zip(new, results):
        prev = state.get(it["ID"], {})
        tries = prev.get("tries", 0) + 1 if res["status"] == "failed" else 0
        if res["status"] == "failed" and tries < 3:      # retried next pass, up to 3 tries
            state[it["ID"]] = {**prev, "tries": tries, "last_error": res.get("why"), "at": now}
            continue
        state[it["ID"]] = {"sig": sig(it), "status": res["status"] if tries < 3 else "gave_up",
                           "key": res.get("key"), "tries": tries, "at": now}
    STATE.write_text(json.dumps(state, indent=1))
    log(f"done: {sum(r['status'] == 'measured' for r in results)} measured, "
        f"{sum(r['status'] == 'left_for_home' for r in results)} left for home, "
        f"{sum(r['status'] == 'failed' for r in results)} failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
