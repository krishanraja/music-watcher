"""Against the target: where a project's latest bounce sits against each brain's measured playlist.

The targets are the medians and middle halves of each person's measured playlist (taste/graph/tracks.csv,
taste/calvin/graph/tracks.csv), the same numbers GENERATION.md reports, recomputed here so they move when the graph
does. The bounce is read with the graph's own feature code (build_graph.features), so both sides are measured the same
way. Evidence, not rules: a brief says where the track sits and never what to change.
"""
from __future__ import annotations

import csv
import statistics
from pathlib import Path

from ..engine import measure as ms

METRICS = [("bpm", "tempo", " BPM"), ("lufs", "loudness", " LUFS"), ("crest_db", "dynamics (crest)", " dB"),
           ("band_sub", "sub band vs the loudest band", " dB"), ("band_air", "air band vs the loudest band", " dB"),
           ("intro_bars_before_first_peak", "bars before the first full-energy section", " bars")]
BRAINS = (("krish", "taste/graph/tracks.csv"), ("calvin", "taste/calvin/graph/tracks.csv"))
MIN_TRACKS = 10


def _num(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def brain_targets(clone: Path) -> dict:
    out = {}
    for who, rel in BRAINS:
        p = Path(clone) / rel
        if not p.exists():
            continue
        with open(p, newline="", encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("measured") == "True"]
        t = {"tracks": len(rows), "source": rel}
        for k, _, _ in METRICS:
            vals = [x for r in rows if (k != "intro_bars_before_first_peak" or r.get("full_track") == "True")
                    and (x := _num(r.get(k))) is not None]
            if len(vals) >= MIN_TRACKS:
                q1, med, q3 = statistics.quantiles(vals, n=4, method="inclusive")
                t[k] = {"median": round(med, 1), "middle_half": [round(q1, 1), round(q3, 1)], "n": len(vals)}
        out[who] = t
    return out


def ours(card: dict, clone: Path) -> dict:
    """The bounce measured as the graph measures a playlist track. A bounce at full energy from its first bar reads as
    0 bars before the first full-energy section (the graph's formula gives -1 when that section starts at bar 0)."""
    f = ms.graph_module(clone).features(card, float(card["duration"]))
    out = {k: f.get(k) for k, _, _ in METRICS}
    if out.get("intro_bars_before_first_peak") is not None:
        out["intro_bars_before_first_peak"] = max(0, out["intro_bars_before_first_peak"])
    return out


def against(card: dict, clone: Path, targets: dict | None = None) -> list[dict]:
    targets = targets if targets is not None else brain_targets(clone)
    mine = ours(card, clone)
    out = []
    for who, t in targets.items():
        lines = []
        for k, label, unit in METRICS:
            v, tk = mine.get(k), t.get(k)
            if v is None or not tk:
                continue
            lo, hi = tk["middle_half"]
            where = "inside the middle half" if lo <= v <= hi else ("above the middle half" if v > hi else "below the middle half")
            lines.append({"what": k, "label": label, "ours": v, "median": tk["median"], "middle_half": [lo, hi],
                          "where": where, "text": f"{label}: ours {v:g}{unit}; {who.title()}'s playlist median "
                                                  f"{tk['median']:g}{unit} (middle half {lo:g} to {hi:g}), {where}."})
        out.append({"brain": who, "tracks": t["tracks"], "source": t["source"], "lines": lines})
    return out
