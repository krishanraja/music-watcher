"""Drop on the cut: a licensed Epidemic Sound track, edited so its measured drop lands on a video's reveal.

trackcard measures the track (its drops and bar grid); Epidemic's EditRecording makes a version of the requested length
and keeps "required regions" of the original at fixed offsets in the edit. This module writes that EditRecording input:
the region from a whole number of bars before the drop (the build) to a whole number of bars after it, placed so the
drop's first beat sits exactly on the reveal. The content engine owns the video; this owns the audio timing.

Epidemic is on the Creator plan: Krish's own channels only, never paid ads (Ruling, Krish, 2026-10-26). Running the edit
and downloading it is the session's step, with the recording id recorded next to the asset.
"""
from __future__ import annotations

import re

from . import grid

MAX_EDIT_MS = 300_000  # EditRecording's targetDurationMs maximum (read 2026-11-24)


class CutError(ValueError):
    pass


def pick_drop(card: dict, which: str = "main") -> dict:
    """The drop to land: the main drop (or the bar given as which="bar:N"); without stems, the first peak section."""
    drops = card.get("drops") or []
    if which != "main" and not re.fullmatch(r"bar:\d+", which or ""):
        raise CutError(f"--drop is main or bar:N (a bar number), not {which!r}")
    if which.startswith("bar:"):
        bar = int(which.split(":", 1)[1])
        d = next((d for d in drops if d.get("bar") == bar), None)
        if d:
            return {"bar": d["bar"], "time_s": float(d["time"]), "source": f"drop at bar {bar}"}
        secs = [s for s in card.get("sections") or [] if s.get("start_bar") == bar]
        if secs:
            return {"bar": bar, "time_s": float(secs[0]["start"]), "source": f"section start at bar {bar}"}
        raise CutError(f"no drop or section starts at bar {bar}")
    d = next((d for d in drops if d.get("main")), None) or (drops[0] if drops else None)
    if d:
        return {"bar": d["bar"], "time_s": float(d["time"]), "source": "main drop" if d.get("main") else "first drop"}
    peak = next((s for s in card.get("sections") or [] if s.get("energy") == "peak" and (s.get("start_bar") or 0) > 1), None)
    if peak:
        return {"bar": peak["start_bar"], "time_s": float(peak["start"]),
                "source": "first peak section (no drops: the card was measured without stems)"}
    raise CutError("the card has no drop and no peak section after bar 1 to land on the cut")


def edit_input(card: dict, length_s: float, hit_s: float, recording_id: str | None = None, which: str = "main",
               lead_bars: int = 4, after_bars: int = 4, audio_format: str = "WAV", max_results: int = 3) -> dict:
    """EditRecording arguments that put the chosen drop on hit_s of a length_s edit.

    lead_bars and after_bars are kept whole; they shrink (never below 0 before, 1 after) when the edit or the track
    is too short to hold them."""
    if length_s <= 0 or not 0 <= hit_s < length_s:
        raise CutError("the hit must fall inside the edit")
    length_ms = int(round(length_s * 1000))
    if length_ms > MAX_EDIT_MS:
        raise CutError(f"Epidemic edits are at most {MAX_EDIT_MS // 1000} s")
    if audio_format not in ("WAV", "MP3"):
        raise CutError("audio_format is WAV or MP3")
    bpm, b1 = grid.project_bpm(card), grid.bar1(card)
    if not bpm or b1 is None:
        raise CutError("the card has no tempo or bar grid")
    bl = grid.bar_len(bpm)
    drop = pick_drop(card, which)
    t = drop["time_s"]
    dur = float(card["duration"])
    lead = max(0, min(lead_bars, int(hit_s // bl), int(t // bl)))
    after = max(1, min(after_bars, int((length_s - hit_s) // bl), int((dur - t) // bl)))
    if (length_s - hit_s) < bl or (dur - t) < bl:
        raise CutError("less than one bar after the hit (or after the drop): nothing of the drop would be heard")
    start_s, end_s = t - lead * bl, t + after * bl
    start_ms, end_ms = int(round(start_s * 1000)), int(round(end_s * 1000))
    offset_ms = int(round(hit_s * 1000)) - (int(round(t * 1000)) - start_ms)
    if offset_ms < 0:  # rounding at an exact fit: trim the region's head by the millisecond, never shift the drop
        start_ms, offset_ms = start_ms - offset_ms, 0
    args = {"input": {
        "targetDurationMs": length_ms,
        "forceDuration": True,
        "downloadAudioFormat": audio_format,
        "maxResults": max_results,
        "requiredRegionsAtOffsets": [{"startMs": start_ms, "endMs": end_ms, "offsetMsInEdit": offset_ms}],
    }}
    if recording_id:
        args = {"id": recording_id, **args}
    return {
        "tool": "EditRecording",
        "args": args,
        "drop": drop,
        "explain": (f"{drop['source']} at bar {drop['bar']} ({t:.2f} s) lands at {hit_s:.2f} s of a {length_s:g} s edit; "
                    f"kept: {lead} bar(s) of build before it and {after} after it ({start_s:.2f}-{end_s:.2f} s of the "
                    f"original), on a {bpm:g} BPM grid ({bl:.3f} s a bar)."),
    }
