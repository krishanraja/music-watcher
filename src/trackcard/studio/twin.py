"""Pro twin by stem: a finished catalog track close to a project's reference, measured stem by stem.

Epidemic Sound's "similar to this Spotify track" returns catalog recordings with separate drums, bass, melody and
instruments stems (low-quality mp3 previews, full length). trackcard measures the full mix (for the bar grid and the
first full-energy section) and each stem without Demucs; this module turns those cards into "when does each layer come
in", and sets that against the project's latest card. Evidence of how one finished track was built, not a rule.

Bars are to the nearest 8 (trackcard's level_by_8_bars blocks), on the twin's own grid. Cards of the twin are measured
from Epidemic's previews and say so; the audio is never committed.
"""
from __future__ import annotations

from . import grid

ENTRY_DB = 15.0  # a stem has come in at the first 8-bar block within this many dB of its own loudest block
OURS_TO_TWIN = {"drums": ("drums",), "bass": ("bass",), "other": ("melody", "instruments"), "vocals": ("vocals",)}
PROVENANCE = "measured by trackcard (Epidemic Sound stem previews, low-quality mp3, full length)"


def entry_bar(stem_card: dict, full_card: dict) -> int | None:
    """First bar (on the full mix's grid, 8-bar resolution) where this stem is within ENTRY_DB of its loudest."""
    lv = [b for b in stem_card.get("level_by_8_bars") or [] if isinstance(b.get("rms_dbfs"), (int, float))]
    if not lv:
        return None
    top = max(b["rms_dbfs"] for b in lv)
    if top <= -60:  # a silent stem (the part is not in this track)
        return None
    first = next(b for b in lv if b["rms_dbfs"] >= top - ENTRY_DB)
    bpm, b1 = grid.project_bpm(full_card), grid.bar1(full_card)
    return max(1, grid.bar_at(first["start"], b1, bpm)) if bpm and b1 is not None else None


def first_peak_bar(card: dict) -> int | None:
    return next((s["start_bar"] for s in card.get("sections") or [] if s.get("energy") == "peak"), None)


def our_entries(card: dict) -> dict:
    """When each of our stems first plays (state active) by section start; None without stems."""
    if not card.get("stems_available"):
        return {}
    out = {}
    for st in OURS_TO_TWIN:
        out[st] = next((max(1, s["start_bar"]) for s in card.get("sections") or []
                        if (s.get("stems") or {}).get(st, {}).get("state") == "active"), None)
    return out


def twin_record(recording: dict, full_card: dict, stem_cards: dict[str, dict], reference: dict | None = None) -> dict:
    """The committed file (engine/productions/<slug>/twins/<recording id>.json)."""
    entries = {name.lower(): entry_bar(c, full_card) for name, c in sorted(stem_cards.items())}
    return {
        "recording_id": recording["id"],
        "title": recording.get("title"),
        "artists": recording.get("artists"),
        "bpm": grid.project_bpm(full_card),
        "key": full_card.get("key"),
        "camelot": full_card.get("camelot"),
        "duration_s": round(float(full_card["duration"]), 1),
        "first_peak_bar": first_peak_bar(full_card),
        "entries": entries,
        "reference": reference,
        "provenance": PROVENANCE,
        "trackcard_version": full_card.get("trackcard_version"),
    }


def against(ours: dict, twin: dict) -> list[str]:
    """Plain lines for the brief: the twin's layer entries and first full-energy section next to ours."""
    mine = our_entries(ours)
    L = []
    for st, names in OURS_TO_TWIN.items():
        theirs = [twin["entries"].get(n) for n in names if twin["entries"].get(n) is not None]
        t = min(theirs) if theirs else None
        if t is None and mine.get(st) is None:
            continue
        label = {"other": "melody and instruments"}.get(st, st)
        a = f"bar {t} (to the nearest 8)" if t is not None else "not in the twin"
        b = f"bar {mine[st]}" if mine.get(st) is not None else ("not measured (no stems)" if not mine else "never")
        L.append(f"{label.capitalize()}: the twin brings it in at {a}; ours at {b}.")
    fp_t, fp_o = twin.get("first_peak_bar"), first_peak_bar(ours)
    if fp_t is not None or fp_o is not None:
        L.append(f"First full-energy section: the twin at bar {fp_t}; ours at bar {fp_o}.")
    return L
