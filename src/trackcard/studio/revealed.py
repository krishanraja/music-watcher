"""Revealed taste: the tracks a person actually replays on Spotify, as a measured layer of their own brain.

Krish's decision (2026-11-24): commit only the Spotify link, title, artists and a rank band to
engine/references/krish/revealed.csv; no play counts, no timestamps. The engine measures each track like a drop
(SoundCloud, within 6 s of Spotify's length) and its card counts in that person's measured layer only, through the
existing measured_extra feed (engine/references/<who>/tracks.csv). Only the person whose Spotify was read: Krish's
listening never reaches Calvin's brain.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path

FIELDS = ["id", "title", "artists", "link", "rank_band"]
BANDS = ("top50", "top200")
VOICES = ("krish", "calvin")
TRACK = re.compile(r"^https://open\.spotify\.com/track/([0-9A-Za-z]{22})$")


class RevealedError(ValueError):
    pass


def path_for(clone: Path, who: str) -> Path:
    return Path(clone) / "engine" / "references" / who / "revealed.csv"


def clean(rows: list[dict]) -> list[dict]:
    out, seen = [], set()
    for r in rows:
        extra = set(r) - set(FIELDS)
        if extra:
            raise RevealedError(f"only {', '.join(FIELDS)} are kept; drop {', '.join(sorted(extra))}")
        m = TRACK.match(str(r.get("link") or ""))
        if not m:
            raise RevealedError(f"link must be https://open.spotify.com/track/<id>: {r.get('link')!r}")
        if r.get("id") and r["id"] != m.group(1):
            raise RevealedError(f"id {r['id']!r} does not match its link")
        if r.get("rank_band") not in BANDS:
            raise RevealedError(f"rank_band is {' or '.join(BANDS)}")
        if not r.get("title"):
            raise RevealedError("every row needs a title")
        tid = m.group(1)
        if tid in seen:
            continue
        seen.add(tid)
        out.append({"id": tid, "title": r["title"].strip(), "artists": (r.get("artists") or "").strip(),
                    "link": r["link"], "rank_band": r["rank_band"]})
    return sorted(out, key=lambda r: (BANDS.index(r["rank_band"]), r["id"]))


def write(clone: Path, who: str, rows: list[dict]) -> Path:
    if who not in VOICES:
        raise RevealedError("who is krish or calvin")
    rows = clean(rows)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    p = path_for(clone, who)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(buf.getvalue(), encoding="utf-8")
    return p


def read(clone: Path, who: str) -> list[dict]:
    p = path_for(clone, who)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
