"""The bar grid a card measures against: bar n starts at bar1_s + (n - 1) * bar length.

A card's drops and sections use this grid (bar 10 of a 126 BPM card whose bar 1 starts at 0.25 s begins at 17.39 s).
"""
from __future__ import annotations

BEATS_PER_BAR = 4  # trackcard assumes 4/4 (card["time_signature"] says so)


def bar_len(bpm: float, beats: int = BEATS_PER_BAR) -> float:
    if not bpm or bpm <= 0:
        raise ValueError("a positive tempo is needed for the bar grid")
    return beats * 60.0 / float(bpm)


def time_of(bar: float, bar1_s: float, bpm: float) -> float:
    """Start of bar `bar` (1-based) in seconds."""
    return float(bar1_s) + (float(bar) - 1) * bar_len(bpm)


def bar_at(t: float, bar1_s: float, bpm: float) -> int:
    """The bar whose start is nearest to time t (1-based; times before bar 1 give 0 or less)."""
    return int(round((float(t) - float(bar1_s)) / bar_len(bpm))) + 1


def project_bpm(card: dict) -> float | None:
    return card.get("likely_project_bpm") or card.get("bpm")


def bar1(card: dict) -> float | None:
    lv = card.get("level_by_8_bars") or []
    return lv[0]["start"] if lv else None
