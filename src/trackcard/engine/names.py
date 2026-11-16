"""New track or new version: read a bounce's file name and decide which project it belongs to.

A name reads `<title> [date] [notes] [vN] [(n)]` in any order after the title, e.g. "Sunrise 11.5 edits.wav",
"Sunrise 11.13 .wav", "Sunrise (1).wav", "late night beat v3.wav", "late beatv2 (2).wav", "sunrise_latest.wav".

- A date in the name wins (M.D, M-D, M_D, optional year, or ISO). M.D is read first; D.M only when the first number
  is over 12. A missing year is the latest year that puts the date no more than 2 days after the file was uploaded.
  No date in the name: the upload date (Drive's created time), and the brief says so.
- Only the trailing run of date, version, copy-mark, qualifier, name, BPM and Camelot words is stripped, never the
  first word, so "Final Hour" and "Remix Culture" keep their titles.
- Same slug -> a new version. A near miss, an empty title or a title of placeholder words only -> a question for a
  person, answered in engine/productions/aliases.json. Otherwise a new track.
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

LOSSLESS = {".wav", ".wave", ".aif", ".aiff", ".flac"}
QUALIFIERS = {"edit", "edits", "mix", "master", "mastered", "mixdown", "premaster", "demo", "bounce", "final", "rough",
              "draft", "wip", "alt", "extended", "dub", "inst", "instrumental", "latest", "new", "export", "version"}
PEOPLE = {"krish", "calvin"}
GENERIC = {"untitled", "audio", "track", "song", "beat", "beats", "idea", "new", "project", "loop", "sketch", "demo"}
NEAR_RATIO = 0.8

_ISO = re.compile(r"(?<!\d)(20\d{2})[-_.](\d{1,2})[-_.](\d{1,2})(?!\d)")
_MD = re.compile(r"(?<![\d.])(\d{1,2})[._-](\d{1,2})(?:[._-](\d{4}|\d{2}))?(?![\d])")
_BRACKET = re.compile(r"[\(\[]([^\)\]]*)[\)\]]")
_VERSION = re.compile(r"^v(\d{1,3})$")
_GLUED = re.compile(r"^(.*[a-z])v(\d{1,3})$")
_BPM = re.compile(r"^\d{2,3}bpm$")
_CAMELOT = re.compile(r"^(1[0-2]|[1-9])[ab]$")


@dataclass(frozen=True)
class Parsed:
    title: str
    slug: str
    date: str | None  # ISO date
    date_source: str  # name | upload
    version: int | None
    note: str
    copy: int | None
    by_hint: str | None
    ext: str
    lossless: bool
    ask: str | None  # why a person must decide, or None


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", fold(title).lower()).strip("-")


def _valid(y: int, m: int, d: int) -> dt.date | None:
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None


def _year_for(m: int, d: int, anchor: dt.date) -> dt.date | None:
    for y in (anchor.year + 1, anchor.year, anchor.year - 1):
        day = _valid(y, m, d)
        if day and day <= anchor + dt.timedelta(days=2):
            return day
    return None


def _find_date(text: str, anchor: dt.date) -> tuple[dt.date | None, tuple[int, int] | None]:
    """The rightmost date in the text and its span."""
    found: list[tuple[int, int, dt.date]] = []
    for m in _ISO.finditer(text):
        day = _valid(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if day:
            found.append((m.start(), m.end(), day))
    for m in _MD.finditer(text):
        if any(s <= m.start() < e for s, e, _ in found):
            continue
        a, b, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if 1 <= a <= 12 and 1 <= b <= 31:
            mo, d = a, b
        elif 1 <= b <= 12 and 13 <= a <= 31:
            mo, d = b, a
        else:
            continue
        if y:
            day = _valid(int(y) + (2000 if len(y) == 2 else 0), mo, d)
        else:
            day = _year_for(mo, d, anchor)
        if day:
            found.append((m.start(), m.end(), day))
    if not found:
        return None, None
    s, e, day = max(found, key=lambda f: f[0])
    return day, (s, e)


def parse(name: str, btime: str) -> Parsed:
    p = Path(name)
    ext = p.suffix.lower()
    stem = fold(p.stem).strip()
    anchor = dt.date.fromisoformat(btime[:10])
    stem = re.sub(r"^copy of\s+", "", stem, flags=re.I)
    notes: list[str] = []
    copy = None
    # Bracketed groups: a copy mark "(2)", a date or an export stamp, or words for the note.
    bracket_text = []
    for m in _BRACKET.finditer(stem):
        inner = m.group(1).strip()
        if re.fullmatch(r"\d{1,3}", inner):
            copy = int(inner)
        elif inner:
            bracket_text.append(inner)
    stem = _BRACKET.sub(" ", stem)
    day, span = _find_date(stem, anchor)
    if span:
        stem = stem[:span[0]] + " " + stem[span[1]:]
    elif bracket_text:
        for i, b in enumerate(bracket_text):
            bday, bspan = _find_date(b, anchor)
            if bday:
                day = bday
                rest = (b[:bspan[0]] + b[bspan[1]:]).strip()
                bracket_text[i] = rest if not re.fullmatch(r"[\d\s_.:-]*", rest) else ""
    by_hint = None
    for b in bracket_text:
        words = [w for w in re.split(r"[\s_]+", b) if w]
        for w in words:
            if w.lower() in PEOPLE:
                by_hint = w.lower()
        if words:
            notes.append(" ".join(words).lower())
    tokens = [t for t in re.split(r"[\s_]+", stem) if t]
    # "version 2" -> v2; glued "beatv2" -> "beat" + v2
    merged: list[str] = []
    for t in tokens:
        if merged and merged[-1].lower() == "version" and t.isdigit():
            merged[-1] = f"v{t}"
            continue
        g = _GLUED.match(t.lower())
        if g and len(g.group(1)) >= 2 and not _VERSION.match(t.lower()):
            merged += [t[:len(g.group(1))], f"v{g.group(2)}"]
        else:
            merged.append(t)
    version = None
    tail: list[str] = []
    while len(merged) > 1:
        t = merged[-1].lower()
        v = _VERSION.match(t)
        if v:
            version = int(v.group(1))
        elif t in QUALIFIERS:
            tail.insert(0, t)
        elif t in PEOPLE:
            by_hint = by_hint or t
        elif _BPM.match(t) or _CAMELOT.match(t) or t == "bpm":
            pass
        else:
            break
        merged.pop()
    if len(merged) == 1:
        v = _VERSION.match(merged[0].lower())
        if v:
            version, merged = int(v.group(1)), []
    title = " ".join(merged).strip()
    slug = slugify(title)
    ask = None
    if not slug:
        ask = "no title in the name"
    elif all(w in GENERIC or w.isdigit() for w in slug.split("-")):
        ask = "the title is only placeholder words"
    return Parsed(title=title, slug=slug, date=(day or anchor).isoformat(), date_source="name" if day else "upload",
                  version=version, note=" ".join(tail + notes), copy=copy, by_hint=by_hint, ext=ext,
                  lossless=ext in LOSSLESS, ask=ask)


def _words(slug: str) -> set[str]:
    return {w for w in slug.split("-") if w and w not in GENERIC and not w.isdigit()}


def near(a: str, b: str) -> bool:
    if SequenceMatcher(None, a, b).ratio() >= NEAR_RATIO:
        return True
    wa, wb = _words(a), _words(b)
    return bool(wa and wb) and (wa <= wb or wb <= wa)


@dataclass(frozen=True)
class Decision:
    kind: str  # version | new | ask | ignore
    project: str | None
    reason: str = ""
    candidates: tuple[str, ...] = ()


def decide(p: Parsed, vid: str, projects: set[str], aliases: dict) -> Decision:
    """projects: the slugs known so far. aliases: engine/productions/aliases.json (keyed by version id or slug)."""
    a = aliases.get(vid) or aliases.get(p.slug) or {}
    if a.get("ignore"):
        return Decision("ignore", None, "ignored in aliases.json")
    if a.get("project"):
        target = slugify(a["project"])
        return Decision("version" if target in projects else "new", target, "aliases.json")
    if p.ask:
        return Decision("ask", None, p.ask)
    if p.slug in projects:
        return Decision("version", p.slug)
    cands = tuple(sorted(s for s in projects if near(p.slug, s)))
    if cands:
        return Decision("ask", None, "close to an existing project", cands)
    return Decision("new", p.slug)
