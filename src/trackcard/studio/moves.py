"""Studio moves for one brief: what a session can do next with Splice, Suno and Epidemic, in the order to try them.

Each move names its tool and arguments as the live connector takes them (read 2026-11-24), its cost and its gate:
  free          searches, previews and analysis: run them, show every result, let the person choose
  standing_yes  uploading a bounce privately to Suno for analysis (Ruling, Krish, 2026-11-24: every new bounce)
  yes_each      anything that spends a credit or writes to an account: ask for that exact call, every time

Character words come only from the accepted rules of the brain whose person owns the next move (the latest bounce's
uploader, unless a session names someone else), never from the other brain, and never from a proposal.

Measured on 2026-11-24 with Splice's describe_a_sound at 124-128 BPM: the brief's own query "bass basslines G minor"
returned 10 of 10 bass loops, 9 of 10 in G; "growly characterful bassline G minor" returned bass loops but none in G;
"brass stab loop" returned 10 of 10 brass, and the same words with "natural organic ... melodic house" returned none.
So the plain query runs first, a character variant runs second with its results filtered by key, and genre words are
never added.
"""
from __future__ import annotations

import hashlib
import math
import re

from ..key import CAMELOT_MAJOR, CAMELOT_MINOR, PITCHES, compatible_camelot, parse_key
from . import grid

# layer -> what to ask a generator for (Suno descriptions and styles)
NOUN = {"drums": "drum groove", "percussion": "percussion loop", "bass": "bassline", "chords": "chord stabs",
        "pads": "warm pad", "fx": "riser", "vocals": "vocal chops", "keys": "keys", "leads": "lead melody",
        "synth": "synth line", "strings": "strings", "guitar": "guitar riff", "brass-and-woodwinds": "brass"}
PITCHED_SKETCH = {"chords", "pads", "keys", "leads", "synth", "strings", "guitar", "brass-and-woodwinds", "bass"}

# accepted claim id -> (layers it speaks to, the words a search or a sketch may carry). Positive claims only.
RULE_WORDS = {
    "sound_design.growl_bass": (("bass",), "growly"),
    "sound_design.percussive_bass": (("bass",), "plucked"),
    "sound_design.organic_textures": (("percussion", "pads", "drums"), "organic"),
    "sound_design.brass": (("brass-and-woodwinds", "leads", "chords"), "brass"),
    "vocal.vocal_chops": (("vocals",), "chopped"),
    "harmony.piano": (("chords", "keys"), "piano"),
    "harmony.lush_chords": (("chords", "pads"), "lush"),
    "harmony.synth_chords": (("chords",), "synth"),
    "groove.melodic_percussion": (("percussion",), "melodic"),
    "mix.crisp_drums": (("drums",), "crisp"),
}

SUNO_SOUND_CREDITS = 2   # sounds-create: two sounds a call, 1 credit each (connector description, 2026-11-24)
SUNO_MIDI_CREDITS = 10   # audio-midi: 10 credits a transcription, charged once when it finishes
SPLICE_DOWNLOAD_CREDITS = 1
SKETCH_BARS = 8
MAX_TWINS = 2
SPOTIFY_ID = re.compile(r"^[0-9A-Za-z]{22}$")


def _id(*parts) -> str:
    return "m-" + hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:8]


def suno_key(key_name: str | None) -> str | None:
    """trackcard's "G minor" as Suno's key enum ("Gm"); None when it cannot be read."""
    if not key_name:
        return None
    try:
        p, major = parse_key(key_name)
    except (ValueError, IndexError):
        return None
    return PITCHES[p] + ("" if major else "m")


def _name(code: str) -> str:
    major = code.endswith("B")
    p = (CAMELOT_MAJOR if major else CAMELOT_MINOR).index(code)
    return f"{PITCHES[p].lower()} {'major' if major else 'minor'}"


def compatible_names(camelot: str | None) -> list[str]:
    return [_name(c) for c in compatible_camelot(camelot)] if camelot else []


def key_ok(result_key: str | None, camelot: str | None) -> bool:
    """A Splice result's Key ("g", "g minor", "a# minor") against the project's key and its Camelot neighbours. A bare
    note matches either mode; a result with no key (unpitched) always passes."""
    if not result_key or not camelot:
        return True
    rk = result_key.strip().lower()
    ok = compatible_names(camelot)
    if rk in ok:
        return True
    if " " not in rk:
        try:
            p, _ = parse_key(rk[:1].upper() + rk[1:])
        except (ValueError, IndexError):
            return False
        return any(n.split(" ")[0] == PITCHES[p].lower() for n in ok)
    try:
        p, major = parse_key(rk)
    except (ValueError, IndexError):
        return False
    return f"{PITCHES[p].lower()} {'major' if major else 'minor'}" in ok


def _filter_keys(camelot: str | None, alt_name: str | None) -> list[str]:
    """Keys a character search keeps: the project's key and its neighbours, and, when trackcard is unsure, also its
    alternative key and that key's neighbours."""
    from .second_ear import camelot_of
    names = compatible_names(camelot)
    alt = camelot_of(alt_name) if alt_name else None
    return names + [n for n in compatible_names(alt) if n not in names]


def owner_words(rules: list[dict], owner: str | None, layer: str) -> tuple[list[str], list[str]]:
    """(words, claim ids) from the owner's brain's accepted rules that speak to this layer."""
    words, ids = [], []
    for r in rules or []:
        if r.get("brain") != owner:
            continue
        for c in r.get("claims") or []:
            spec = RULE_WORDS.get(c.get("id"))
            if spec and layer in spec[0] and spec[1] not in words:
                words.append(spec[1])
                ids.append(c["id"])
    return words, ids


def _gap_moves(slug: str, title: str, g: dict, ctx: dict, rules: list[dict], owner: str | None) -> list[dict]:
    layer, bars = g.get("layer", ""), g.get("bars", "")
    gap = {"rule": g.get("rule"), "layer": layer, "bars": bars}
    sp = g.get("splice") or {}
    args = dict(sp.get("args") or {})
    camelot = (ctx.get("key") or {}).get("camelot")
    key_name = (ctx.get("key") or {}).get("name")
    bpm = (ctx.get("tempo") or {}).get("bpm")
    pitched = layer not in ("drums", "percussion", "fx")
    alt = (ctx.get("key") or {}).get("alternative")
    unsure = bool(pitched and (sp.get("key_confirm_needed") or alt))  # trackcard is unsure between two keys
    confirm = {"key_confirm_needed": True} if unsure else {}
    rid = g.get("rule")  # two rules can name the same layer and bars (R6 and R8 on a bare section): ids keep them apart
    out = []
    if args.get("query"):
        out.append({"id": _id(slug, "splice", layer, bars, rid, "plain"), "kind": "splice_search", "provider": "splice",
                    "gate": "free", "cost": {"credits": 0}, "gap": gap, "owner_brain": owner,
                    "tool": "describe_a_sound", "args": args,
                    **confirm,
                    "then": "Show every result as numbered. A download spends 1 Splice credit: ask for that exact sound. "
                            "Build a stack only around a loop, with generate_public_url false.",
                    "why": f"{g.get('gap')} (bars {bars})"})
    words, ids = owner_words(rules, owner, layer)
    if words and args.get("query"):
        base = re.sub(rf"\s*{re.escape(str(key_name))}$", "", args["query"]) if key_name else args["query"]
        cargs = {**args, "query": f"{' '.join(words)} {base}".strip()}
        out.append({"id": _id(slug, "splice", layer, bars, rid, "character", *ids), "kind": "splice_search", "provider": "splice",
                    "gate": "free", "cost": {"credits": 0}, "gap": gap, "owner_brain": owner, "tool": "describe_a_sound",
                    "args": cargs, "rules": ids, **confirm,
                    **({"post_filter": {"keys": _filter_keys(camelot, alt if unsure else None),
                                        "how": "keep results whose Key is one of these; a bare note matches either mode; "
                                               "a result with no key passes"}} if pitched and camelot else {}),
                    "then": "Run after the plain search. Character words move results off key (measured 2026-11-24), "
                            "so filter by key before showing them.",
                    "why": f"{owner.title() if owner else 'The owner'}'s approved rule(s) {', '.join(ids)} speak to {layer}."})
    sk = None if unsure else suno_key(key_name)  # a paid call never guesses between two keys
    ask_key = " trackcard is unsure of the key: confirm it first and add it to the arguments." if unsure else ""
    if pitched and bpm:
        sargs = {"description": " ".join([*words, NOUN.get(layer, layer)]), "loop": True, "tempo": int(round(bpm))}
        if sk:
            sargs["key"] = sk
        out.append({"id": _id(slug, "suno_sound", layer, bars, rid), "kind": "suno_sound", "provider": "suno",
                    "gate": "yes_each", "cost": {"credits": SUNO_SOUND_CREDITS}, "gap": gap, "owner_brain": owner,
                    "tool": "sounds-create", "args": sargs, **confirm,
                    "then": "Only when Splice has nothing that fits. Two loops come back; the person picks one or none."
                            + ask_key,
                    "why": f"A loop made at the project's own tempo and key for {layer}, bars {bars}."})
    if layer in PITCHED_SKETCH and bpm and (sk or unsure):
        secs = SKETCH_BARS * grid.bar_len(bpm)
        style = ", ".join([*words, NOUN.get(layer, layer), "instrumental", f"{int(round(bpm))} BPM",
                           *([key_name] if sk else []), f"{SKETCH_BARS} bars", "sparse"])
        out.append({"id": _id(slug, "suno_sketch_midi", layer, bars, rid), "kind": "suno_sketch_midi", "provider": "suno",
                    **confirm,
                    "gate": "yes_each", "cost": {"credits": None, "note": "audio-create at suno.com's song price (read "
                                                 "account-usage before and after and record it), then 10 for the MIDI"},
                    "gap": gap, "owner_brain": owner,
                    "steps": [{"tool": "audio-create", "args": {"instrumental": True, "style": style,
                                                                "title": f"{title} {layer} sketch, bars {bars}",
                                                                "duration": max(15, math.ceil(secs))}},
                              {"tool": "audio-midi", "args": {"id": "<the sketch the person picked>"},
                               "cost": {"credits": SUNO_MIDI_CREDITS}}],
                    "then": "Notes, not sounds: only the MIDI goes into Ableton, played with their own sounds. The "
                            "sketch audio never goes into the track. Record the pick with its Suno id hashed." + ask_key,
                    "why": f"Melodic ideas for {layer}, bars {bars}, at {int(round(bpm))} BPM"
                           + (f" in {key_name}." if sk else " (key to confirm).")})
    return out


def plan_moves(brief: dict, rules: list[dict] | None = None, owner: str | None = None) -> list[dict]:
    """Every move for a brief, free ones first. owner: whose next move it is (default: the latest bounce's uploader)."""
    slug, title = brief["project"]["slug"], brief["project"]["title"]
    ctx, vid = brief["context"], brief["latest_version"]
    if owner is None:
        owner = next((v.get("by") for v in brief.get("versions") or [] if v["id"] == vid), None)
    rules = rules if rules is not None else brief.get("rules") or []
    moves = [{"id": _id(slug, "second_ear", vid), "kind": "suno_second_ear", "provider": "suno", "gate": "standing_yes",
              "cost": {"credits": 0}, "gap": None, "owner_brain": owner,
              "steps": [{"tool": "audio-upload-create", "args": {"title": f"{vid} (private, for analysis)"}},
                        {"tool": "audio-upload-complete", "args": {"id": "<the upload's clip id>"}},
                        {"tool": "audio-analysis", "args": {"id": "<the upload's clip id>"}}],
              "then": f"Keep the song private. Save the analysis JSON outside the repository, then run "
                      f"`trackcard studio ear {slug} --analysis <file>`. The Suno id is never written down.",
              "why": "A second measurement of this bounce: the brief's bar numbers, tempo, key and sections are checked "
                     "where two machines disagree (Ruling, Krish, 2026-11-24: every new bounce may be uploaded)."}]
    for g in brief.get("gaps") or []:
        moves += _gap_moves(slug, title, g, ctx, rules, owner)
    twins = [r for r in brief.get("references") or [] if SPOTIFY_ID.match(str(r.get("id") or ""))][:MAX_TWINS]
    for r in twins:
        moves.append({"id": _id(slug, "twin", r["id"]), "kind": "epidemic_twin", "provider": "epidemic", "gate": "free",
                      "cost": {"credits": 0}, "gap": None, "owner_brain": owner,
                      "reference": {"id": r["id"], "title": r.get("title"), "artists": r.get("artists")},
                      "steps": [{"tool": "SearchRecordings",
                                 "args": {"query": {"externalID": {"type": "SPOTIFY_TRACK", "id": r["id"]}}, "first": 5}}],
                      "then": "Pick the result nearest the project's tempo, measure its full-mix preview and each stem "
                              "preview with `trackcard analyze --no-stems`, then `trackcard studio twin "
                              f"{slug} ...`. Previews are for measuring only; nothing is downloaded with a licence.",
                      "why": f"A finished catalog track close to {r.get('artists')} - {r.get('title')}, with stems, "
                             "shows when each layer comes in."})
    order = {"free": 0, "standing_yes": 1, "yes_each": 2}
    return sorted(moves, key=lambda m: (order[m["gate"]], m["kind"] != "suno_second_ear"))
