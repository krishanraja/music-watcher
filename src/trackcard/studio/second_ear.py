"""Second ear: Suno's analysis of a bounce, set against trackcard's card, so people listen only where the two disagree.

A bounce is uploaded privately to Suno (a standing yes for every new bounce, Krish's and Calvin's: Ruling, Krish,
2026-11-24) and Suno's audio analysis (free) returns a beat map with bar positions, tempo, key and sections. This module
compares that with the card and writes ear-check questions. It never sees audio or a Suno id: the session passes the
analysis JSON in, and only the comparison is committed.

The analysis shape follows the Suno connector's description read on 2026-11-24 (beats with bar_position, bpm,
time_signature, key; sections with label and duration_s). The parser is tolerant of where those fields sit, and says
what it could not read rather than guessing.
"""
from __future__ import annotations

import re

from ..key import CAMELOT_MAJOR, CAMELOT_MINOR, parse_key
from . import grid

TEMPO_TOL_BPM = 0.5
BOUNDARY_TOL_BARS = 1
DOWNBEAT_TOL_BEATS = 0.25


def camelot_of(text: str | None) -> str | None:
    if not text:
        return None
    t = str(text).strip().replace("♯", "#").replace("♭", "b")
    m = re.fullmatch(r"([A-Ga-g][#b]?)\s*(major|maj|minor|min|m)?\.?", t, re.I)
    if m:  # "G minor", "G Minor", "Gmin", "gm", "G": parse_key reads the lower-case words
        q = (m.group(2) or "").lower()
        t = m.group(1)[0].upper() + m.group(1)[1:] + (" minor" if q in ("minor", "min", "m") else " major")
    try:
        p, major = parse_key(t)
    except (ValueError, IndexError):
        return None
    return (CAMELOT_MAJOR if major else CAMELOT_MINOR)[p]


def _find(d: dict, *keys):
    """The first of keys found at the top level or one level down (e.g. analysis["beats"]["bpm"])."""
    for k in keys:
        if isinstance(d.get(k), (int, float, str)) and d.get(k) != "":
            return d[k]
    for v in d.values():
        if isinstance(v, dict):
            for k in keys:
                if isinstance(v.get(k), (int, float, str)) and v.get(k) != "":
                    return v[k]
    return None


def _list(d: dict, key: str) -> list:
    v = d.get(key)
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        for k in (key, "items", "list", "data"):
            if isinstance(v.get(k), list):
                return v[k]
    return []


def _t(x: dict, *keys) -> float | None:
    for k in keys:
        if isinstance(x.get(k), (int, float)):
            return float(x[k])
    return None


def read_analysis(a: dict) -> dict:
    """Normalise Suno's analysis: bpm, key (and its Camelot code), downbeat times, section starts with labels."""
    beats = _list(a, "beats")
    downbeats = [t for b in beats if isinstance(b, dict) and b.get("bar_position") == 1
                 and (t := _t(b, "time_s", "time", "start_s", "start", "t")) is not None]
    secs, at, unread = [], 0.0, []
    for s in _list(a, "sections"):
        if not isinstance(s, dict):
            continue
        start = _t(s, "start_s", "start", "time_s", "time")
        dur = _t(s, "duration_s", "duration")
        if start is None:
            start = at
        secs.append({"start_s": round(start, 3), "label": s.get("label")})
        if dur is not None:
            at = start + dur
    bpm = _find(a, "bpm", "tempo")
    try:
        bpm = float(bpm) if bpm is not None else None
    except (TypeError, ValueError):
        bpm = None
    if bpm is not None and bpm <= 0:
        bpm = None
    key = _find(a, "key")
    if bpm is None:
        unread.append("tempo")
    if key is None:
        unread.append("key")
    if not downbeats:
        unread.append("downbeats (beats with bar_position 1)")
    if not secs:
        unread.append("sections")
    return {"bpm": bpm, "key": key, "camelot": camelot_of(key),
            "downbeats": downbeats, "sections": secs, "unread": unread}


def _relative(a: str, b: str) -> bool:
    return a[:-1] == b[:-1] and a[-1] != b[-1]


def compare(card: dict, analysis: dict) -> dict:
    """Agreements and ear-check questions. Bars are trackcard's (the bar numbers in the brief)."""
    s = read_analysis(analysis)
    bpm, b1 = grid.project_bpm(card), grid.bar1(card)
    out: dict = {"tempo": None, "key": None, "grid": None, "sections": None, "questions": [], "unread": s["unread"]}
    q = out["questions"]
    if bpm and s["bpm"]:
        best = min((abs(bpm - s["bpm"] * k), k) for k in (1, 2, 0.5))
        agree = best[0] <= TEMPO_TOL_BPM
        out["tempo"] = {"trackcard": bpm, "suno": s["bpm"], "agree": agree, "octave": best[1] != 1}
        if not agree:
            q.append({"what": "tempo", "text": f"Tempo: trackcard measures {bpm:g} BPM, Suno hears {s['bpm']:g}. "
                      "Which is the project tempo? If trackcard is wrong, give \"bpm\" in aliases.json: every bar number "
                      "in the brief depends on it."})
    ours, alt = card.get("camelot"), card.get("key_alternative_camelot")
    if ours and s["camelot"]:
        rel = _relative(ours, s["camelot"])
        same = ours == s["camelot"]
        out["key"] = {"trackcard": card.get("key"), "suno": s["key"], "agree": same or rel, "relative": rel,
                      "settles_alternative": bool(alt) and s["camelot"] == alt}
        if alt and s["camelot"] in (ours, alt):
            pick = card.get("key") if s["camelot"] == ours else card.get("key_alternative")
            q.append({"what": "key", "text": f"Key: trackcard was unsure between {card.get('key')} and "
                      f"{card.get('key_alternative')}; Suno hears {s['key']}, which points to {pick}. Confirm by ear, "
                      "then give \"key\" in aliases.json."})
        elif not (same or rel):
            q.append({"what": "key", "text": f"Key: trackcard measures {card.get('key')} ({ours}), Suno hears "
                      f"{s['key']} ({s['camelot']}). Which is it?"})
    elif s["key"] and not s["camelot"]:
        out["unread"].append(f"key {s['key']!r} (not a key trackcard can read)")
    if bpm and b1 is not None and s["downbeats"]:
        bl = grid.bar_len(bpm)
        beat = bl / grid.BEATS_PER_BAR
        first = s["downbeats"][0]
        phase = ((first - b1) / beat) % grid.BEATS_PER_BAR
        off = min(phase, grid.BEATS_PER_BAR - phase)
        out["grid"] = {"suno_first_downbeat_s": round(first, 3), "trackcard_bar1_s": b1, "offset_beats": round(off, 2),
                       "agree": off <= DOWNBEAT_TOL_BEATS}
        if off > DOWNBEAT_TOL_BEATS:
            q.append({"what": "grid", "text": f"Bar 1: Suno's downbeats sit {off:.1f} beat(s) away from trackcard's bar "
                      "lines. If Suno is right, the bar numbers in the brief are shifted: check where bar 1 is."})
    if bpm and b1 is not None and s["sections"]:
        theirs = sorted({b for x in s["sections"] if (b := grid.bar_at(x["start_s"], b1, bpm)) > 1})  # as trackcard's
        mine = sorted({x["start_bar"] for x in card.get("sections") or [] if (x.get("start_bar") or 0) > 1})
        only_suno = [b for b in theirs if not any(abs(b - m) <= BOUNDARY_TOL_BARS for m in mine)]
        only_tc = [m for m in mine if not any(abs(b - m) <= BOUNDARY_TOL_BARS for b in theirs)]
        out["sections"] = {"trackcard_starts": mine, "suno_starts": theirs, "only_suno": only_suno, "only_trackcard": only_tc,
                           "agree": not only_suno and not only_tc}
        for b in only_suno:
            q.append({"what": "section", "bar": b, "text": f"Bar {b} ({_mmss(grid.time_of(b, b1, bpm))}): Suno hears a "
                      "new section here; trackcard does not. Listen: does something change?"})
        for m in only_tc:
            q.append({"what": "section", "bar": m, "text": f"Bar {m} ({_mmss(grid.time_of(m, b1, bpm))}): trackcard "
                      "starts a section here; Suno hears none. Listen: is it a real change?"})
    return out


def _mmss(s: float) -> str:
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def record(card: dict, analysis: dict, version_id: str, on: str) -> dict:
    """The committed file (engine/productions/<slug>/ear/<version id>.json): the comparison only, never a Suno id."""
    return {"version": version_id, "on": on, "source": "Suno audio analysis of the bounce (private upload)",
            "trackcard_version": card.get("trackcard_version"), **compare(card, analysis)}
