"""Per project: BRIEF.md (for people and Claude) and brief.json (for the UI and the MCP adapters), plus engine/STATUS.md.

Everything here is derived from the registry, the cards and the brains' accepted claims. No run timestamps: the same
inputs give the same bytes. Rules are a pointer view of each brain's APPROVED list, labelled by brain; an adapter re-reads
APPROVED.md before acting and never applies one brain's rules as the other's.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

SCHEMA_VERSION = 1
UNPITCHED = {"drums", "percussion", "fx"}
STEMS = ("drums", "bass", "vocals", "other")


# ---------------------------------------------------------------- order

def order_key(vid: str, v: dict) -> tuple:
    return (v.get("date") or "", v.get("version") or 0, v.get("btime") or "", vid)


def ordered(versions: dict) -> list[tuple[str, dict]]:
    return sorted(versions.items(), key=lambda kv: order_key(*kv))


def measured(versions: dict) -> list[tuple[str, dict]]:
    return [(k, v) for k, v in ordered(versions) if v.get("status") == "measured"]


def latest(versions: dict) -> tuple[str | None, bool]:
    """(version id, project_is_archived). Newest measured version not in Archive/; else the newest archived one."""
    # a version is still there when its file is, or when a present re-upload of the same bytes points at it
    alive = {v.get("copy_of") for v in versions.values() if v.get("status") == "copy_of" and v.get("present", True)}
    ms = [(k, v) for k, v in measured(versions) if v.get("present", True) or k in alive]
    present = [v for v in versions.values() if v.get("present", True)]
    archived = bool(present) and all(v_folder(v) == "archive" for v in present)
    live = [kv for kv in ms if v_folder(kv[1]) != "archive"]
    if live:
        return live[-1][0], False
    return (ms[-1][0] if ms else None), archived


def v_folder(v: dict) -> str:
    return v.get("folder", "production")


# ---------------------------------------------------------------- reading a card

def _bars(text: str) -> list[tuple[int, int]]:
    out = []
    for a, b in re.findall(r"(\d+)\s*-\s*(\d+)", text or ""):
        out.append((int(a), int(b)))
    return out


def _bpm_ints(rng: str) -> tuple[int | None, int | None]:
    m = re.match(r"\s*(\d+)\s*-\s*(\d+)", rng or "")
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def main_drop(card: dict) -> dict | None:
    drops = card.get("drops")
    if not drops:
        return None
    m = next((d for d in drops if d.get("main")), None)
    return {"bar": m["bar"], "time_s": round(m["time"], 1)} if m else None


def stem_density(card: dict) -> dict | None:
    if not card.get("stems_available"):
        return None
    secs = card["sections"]
    tot = sum(s["end"] - s["start"] for s in secs) or 1
    return {st: round(sum(s["stems"][st]["density"] * (s["end"] - s["start"]) for s in secs) / tot, 2) for st in STEMS}


def bars_total(card: dict) -> int:
    return max((s.get("end_bar") or 0) for s in card["sections"]) if card.get("sections") else 0


def fmt_time(s: float) -> str:
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


# ---------------------------------------------------------------- diff

def diff(prev: dict, cur: dict) -> dict:
    """What changed between two cards. Stem-derived fields only when both were measured with stems."""
    both_stems = bool(prev.get("stems_available") and cur.get("stems_available"))
    ch: dict = {
        "duration_s": [round(prev["duration"], 1), round(cur["duration"], 1)],
        "bars": [bars_total(prev), bars_total(cur)],
        "bpm": [prev.get("likely_project_bpm") or prev.get("bpm"), cur.get("likely_project_bpm") or cur.get("bpm")],
        "key": [prev.get("key"), cur.get("key")],
        "sections": [len(prev.get("sections") or []), len(cur.get("sections") or [])],
        "lufs": [(prev.get("loudness") or {}).get("integrated_lufs"), (cur.get("loudness") or {}).get("integrated_lufs")],
        "crest_db": [(prev.get("loudness") or {}).get("crest_db"), (cur.get("loudness") or {}).get("crest_db")],
        "comparable_stems": both_stems,
    }
    if both_stems:
        ch["main_drop"] = [main_drop(prev), main_drop(cur)]
        ch["stem_density"] = [stem_density(prev), stem_density(cur)]
        ch["gaps"] = gap_changes(prev.get("brief") or [], cur.get("brief") or [])
    return ch


def _gap_key(g: dict) -> tuple[str, str]:
    return (g.get("rule", ""), g.get("layer", ""))


def _overlap(a: dict, b: dict) -> bool:
    ra, rb = _bars(a.get("bars", "")), _bars(b.get("bars", ""))
    if any(x0 <= y1 and y0 <= x1 for x0, x1 in ra for y0, y1 in rb):
        return True
    return a.get("bars") == b.get("bars") == "any"


def gap_changes(prev: list[dict], cur: list[dict]) -> dict:
    """Pair gaps by (rule, layer) and overlapping bars, so renumbered sections do not read as new gaps."""
    used: set[int] = set()
    still, opened = [], []
    for g in cur:
        j = next((i for i, p in enumerate(prev) if i not in used and _gap_key(p) == _gap_key(g) and _overlap(p, g)), None)
        if j is None:
            opened.append(g)
        else:
            used.add(j)
            still.append(g)
    closed = [p for i, p in enumerate(prev) if i not in used]
    short = lambda g: {"rule": g.get("rule"), "layer": g.get("layer"), "bars": g.get("bars"), "gap": g.get("gap")}
    return {"closed": [short(g) for g in closed], "opened": [short(g) for g in opened], "still_open": len(still)}


# ---------------------------------------------------------------- adapters

def splice_args(g: dict, card: dict) -> dict:
    lo, hi = _bpm_ints(g.get("bpm_range", ""))
    layer = g.get("layer", "")
    query = " ".join([layer] + list(g.get("tags") or [])[:1]).strip()
    out = {"tool": "describe_a_sound", "args": {"query": query, "type": "loop"}}
    if lo is not None:
        out["args"].update(bpm_min=lo, bpm_max=hi)
    if layer not in UNPITCHED:
        if card.get("key_alternative"):
            out["key_confirm_needed"] = True
        else:
            out["args"]["query"] = f"{query} {card.get('key')}".strip()
    return out


def context(card: dict) -> dict:
    lv = card.get("level_by_8_bars") or []
    return {
        "tempo": {"bpm": card.get("likely_project_bpm") or card.get("bpm"), "measured_bpm": card.get("bpm"),
                  "source": card.get("bpm_source"), "confidence": card.get("bpm_confidence"),
                  "octave_corrected": card.get("octave_corrected")},
        "bar1_s": lv[0]["start"] if lv else None,
        "key": {"name": card.get("key"), "camelot": card.get("camelot"), "source": card.get("key_source"),
                "confidence": card.get("key_confidence"), "alternative": card.get("key_alternative"),
                "compatible": card.get("compatible_keys")},
        "duration_s": round(card["duration"], 1),
        "sections": [{"id": s["id"], "label": s["label"], "start_bar": s["start_bar"], "end_bar": s["end_bar"],
                      "start_s": round(s["start"], 2), "end_s": round(s["end"], 2), "energy": s["energy"]}
                     for s in card.get("sections") or []],
        "label_is_fallback": card.get("section_method") != "allin1",
        "drops": ([{"bar": d["bar"], "time_s": round(d["time"], 2), "main": bool(d.get("main"))}
                   for d in card.get("drops") or []] if card.get("stems_available") else None),
        "loudness": card.get("loudness"),
    }


def gaps(card: dict) -> list[dict]:
    out = []
    for g in card.get("brief") or []:
        out.append({**g, "bar_ranges": [list(r) for r in _bars(g.get("bars", ""))], "splice": splice_args(g, card),
                    "stack_layer": {"layer_type": g.get("layer")}})
    return out


# ---------------------------------------------------------------- references that fit

def _camelot_ok(a: str, b: str) -> bool:
    ma, mb = re.match(r"(\d+)([AB])", a or ""), re.match(r"(\d+)([AB])", b or "")
    if not ma or not mb:
        return False
    na, la, nb, lb = int(ma.group(1)), ma.group(2), int(mb.group(1)), mb.group(2)
    if la == lb:
        return min((na - nb) % 12, (nb - na) % 12) <= 1
    return na == nb


def _bpm_ok(a: float, b: float) -> bool:
    return any(abs(x - b) <= 3 for x in (a, a * 2, a / 2))


def reference_rows(clone: Path) -> list[dict]:
    rows = []
    sources = [(clone / "engine" / "references" / "index.csv", None),
               (clone / "taste" / "graph" / "tracks.csv", "Krish's playlist"),
               (clone / "taste" / "calvin" / "graph" / "tracks.csv", "Calvin's playlist")]
    for path, label in sources:
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("measured") not in ("True", "true", None) and label:
                    continue
                src = label or ("shared by " + " and ".join(w.title() for w in (r.get("who") or "").split(";") if w)
                                if r.get("who") else "a reference")
                rows.append({"id": r.get("id") or r.get("key"), "title": r.get("title"), "artists": r.get("artists"),
                             "bpm": r.get("bpm"), "camelot": r.get("camelot"), "source": src})
    return rows


def references_that_fit(rows: list[dict], bpm, camelot: str, limit: int = 8) -> list[dict]:
    out, seen = [], set()
    for r in rows:
        try:
            b = float(r["bpm"])
        except (TypeError, ValueError):
            continue
        if bpm is None or not _bpm_ok(b, float(bpm)) or not _camelot_ok(r.get("camelot"), camelot):
            continue
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        out.append({**r, "bpm": round(b)})
    out.sort(key=lambda r: (abs(r["bpm"] - float(bpm)), r["title"] or ""))
    return out[:limit]


# ---------------------------------------------------------------- the brief

def project_brief(slug: str, proj: dict, cards: Path, rules: list[dict], refs: list[dict]) -> tuple[str, dict] | None:
    versions = proj["versions"]
    vid, archived = latest(versions)
    if vid is None:
        return None
    card = json.loads((cards / f"{vid}.trackcard.json").read_text(encoding="utf-8"))
    order = [k for k, _ in ordered(versions)]
    ms = [k for k, _ in measured(versions)]
    prev_vid = ms[ms.index(vid) - 1] if ms.index(vid) > 0 else None
    changes = None
    if prev_vid:
        prev = json.loads((cards / f"{prev_vid}.trackcard.json").read_text(encoding="utf-8"))
        changes = {"from": prev_vid, "to": vid, **diff(prev, card)}
    v = versions[vid]
    ctx = context(card)
    fit = references_that_fit(refs, ctx["tempo"]["bpm"], card.get("camelot"))
    data = {
        "schema_version": SCHEMA_VERSION,
        "project": {"slug": slug, "title": proj["title"], "archived": archived},
        "as_of": v["date"],
        "latest_version": vid,
        "source_card": f"engine/productions/cards/{vid}.trackcard.json",
        "trackcard_version": card.get("trackcard_version"),
        "context": ctx,
        "gaps": gaps(card),
        "gaps_partial": None if card.get("stems_available") else "measured without stems: drum, bass and harmony gaps not checked",
        "changes": changes,
        "rules": rules,
        "references": fit,
        "versions": [{"id": k, "n": i + 1, "date": versions[k]["date"], "date_source": versions[k]["date_source"],
                      "note": versions[k].get("note", ""), "version": versions[k].get("version"),
                      "by": versions[k].get("by"), "folder": v_folder(versions[k]), "status": versions[k]["status"],
                      "source_name": versions[k]["source_name"]} for i, k in enumerate(order)],
    }
    return render_md(data, card), data


def _who(w: str | None) -> str:
    return {"krish": "Krish", "calvin": "Calvin"}.get(w or "", "someone not in the engine's people list")


def _delta(a, b, unit: str, nd: int = 1) -> str:
    if a is None or b is None:
        return "n/a"
    if a == b:
        return f"{b}{unit} (no change)"
    d = round(b - a, nd) if isinstance(a, (int, float)) and isinstance(b, (int, float)) else None
    return f"{a}{unit} -> {b}{unit}" + (f" ({d:+}{unit})" if d is not None else "")


def render_md(d: dict, card: dict) -> str:
    p, ctx, vs = d["project"], d["context"], d["versions"]
    nums = {x["id"]: x["n"] for x in vs}
    lat = next(x for x in vs if x["id"] == d["latest_version"])
    L = [f"# {p['title']}: production brief", "",
         "Generated by the production engine (`trackcard engine run`) from the measured versions in "
         "`engine/productions/registry.json`. Do not edit; edit `aliases.json` or the bounce's name instead.",
         "Measured by trackcard on the full bounce. Rules come only from each brain's approved list.", ""]
    if p["archived"]:
        L += ["**Archived project:** every version is in Drive's Archive folder.", ""]
    dsrc = "from the file name" if lat["date_source"] == "name" else "the upload date: the name has no date"
    L += ["## Where it stands", "",
          f"- Latest: version {lat['n']} of {len(vs)}, {lat['date']} ({dsrc}), `{lat['source_name']}`"
          + (f", note \"{lat['note']}\"" if lat["note"] else "") + f", uploaded by {_who(lat['by'])}.",
          f"- First version: {vs[0]['date']}.",
          f"- {ctx['tempo']['bpm']} BPM ({ctx['tempo']['confidence']} confidence), {ctx['key']['name']} "
          f"({ctx['key']['camelot']}, {ctx['key']['confidence']} confidence"
          + (f"; also likely {ctx['key']['alternative']}" if ctx['key']['alternative'] else "") + f"), "
          f"{fmt_time(ctx['duration_s'])}, {(ctx['loudness'] or {}).get('integrated_lufs')} LUFS.",
          ]
    md = main_drop(card)
    L.append(f"- Main drop: bar {md['bar']} ({fmt_time(md['time_s'])})." if md else
             "- Main drop: not measured (no stems)." if not card.get("stems_available") else "- Main drop: none found.")
    L.append("")
    ch = d["changes"]
    L += ["## What changed since the previous version", ""]
    if not ch:
        L += ["First measured version: nothing to compare yet.", ""]
    else:
        L += [f"From version {nums[ch['from']]} to version {nums[ch['to']]}:", "",
              f"- Length: {fmt_time(ch['duration_s'][0])} -> {fmt_time(ch['duration_s'][1])}, bars {_delta(*ch['bars'], '')}.",
              f"- Tempo: {_delta(*ch['bpm'], ' BPM')}. Key: {_delta(*ch['key'], '')}.",
              f"- Sections: {_delta(*ch['sections'], '')}.",
              f"- Loudness: {_delta(*ch['lufs'], ' LUFS')}; crest {_delta(*ch['crest_db'], ' dB')}."]
        if ch["comparable_stems"]:
            a, b = ch["main_drop"]
            L.append(f"- Main drop: {('bar ' + str(a['bar'])) if a else 'none'} -> {('bar ' + str(b['bar'])) if b else 'none'}.")
            sa, sb = ch["stem_density"]
            moves = [f"{st} {sa[st]:.0%} -> {sb[st]:.0%}" for st in STEMS if abs(sb[st] - sa[st]) >= 0.05]
            L.append("- Stems sounding (share of the track): " + ("; ".join(moves) if moves else "no change of 5 points or more") + ".")
            g = ch["gaps"]
            for x in g["closed"]:
                L.append(f"- Gap closed: {x['gap']} (bars {x['bars']}, {x['layer']}, rule {x['rule']}).")
            for x in g["opened"]:
                L.append(f"- New gap: {x['gap']} (bars {x['bars']}, {x['layer']}, rule {x['rule']}).")
            L.append(f"- Gaps still open: {g['still_open']}.")
        else:
            L.append("- Drops, stems and gaps: not comparable (one of the two versions was measured without stems).")
        L.append("")
    if any(x["status"] != "measured" for x in vs) or len(vs) > 1:
        L += ["## Versions", "", "| # | date | note | file | by | where | status |", "|---|---|---|---|---|---|---|"]
        for x in vs:
            L.append(f"| {x['n']} | {x['date']}{'' if x['date_source'] == 'name' else ' (upload)'} | {x['note']} | "
                     f"`{x['source_name']}` | {_who(x['by']) if x['by'] else ''} | {x['folder']} | {x['status']} |")
        L.append("")
    L += ["## Section map (latest)", "",
          "Labels are " + ("cluster numbers from the fallback segmenter, not musical functions." if ctx["label_is_fallback"]
                           else "from allin1."), "",
          "| section | bars | time | energy |", "|---|---|---|---|"]
    for s in ctx["sections"]:
        L.append(f"| {s['label']} | {s['start_bar']}-{s['end_bar']} | {fmt_time(s['start_s'])}-{fmt_time(s['end_s'])} | {s['energy']} |")
    L += ["", "## Gaps to fill (Splice)", ""]
    if d["gaps_partial"]:
        L += [f"Partial: {d['gaps_partial']}.", ""]
    if not d["gaps"]:
        L.append("No gaps measured.")
    for g in d["gaps"]:
        sp = g["splice"]
        L.append(f"- **{g['layer']}**, bars {g['bars']}: {g['gap']}. {g['instruction']}"
                 + (" Confirm the key first: trackcard is unsure between two." if sp.get("key_confirm_needed") else ""))
    L += ["", "## What the brains have approved", "",
          "Pointers only: re-read each brain's `APPROVED.md` before acting, and never apply one brain's rules as the other's.", ""]
    for r in d["rules"]:
        head = f"- **{r['brain'].title()}'s brain** (`{r['approved_md']}`, decided by {r['decided_by']})"
        L.append(head + (": none accepted yet." if not r["claims"] else ":"))
        for c in r["claims"]:
            L.append(f"  - `{c['id']}`: {c['text']}")
    L += ["", "## References that fit", "",
          "Within 3 BPM (or half or double time) and a Camelot match or neighbour of the latest version.", ""]
    if not d["references"]:
        L.append("None of the measured references or playlist tracks fit yet.")
    for r in d["references"]:
        L.append(f"- {r['artists']} - {r['title']}: {r['bpm']} BPM, {r['camelot']} ({r['source']})")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- STATUS.md

def status_md(registry: dict, listing_counts: dict, extra: list[str] | None = None) -> str:
    L = ["# Production engine: status", "",
         "Generated by `trackcard engine run`. State only: what is in, what waits for a person. What is new in a run is",
         "in the engine's pull request, not here.", "",
         "## Projects", "", "| project | versions | latest | measured | queued | gave up |", "|---|---|---|---|---|---|"]
    for slug, p in sorted(registry["projects"].items()):
        vs = p["versions"]
        vid, archived = latest(vs)
        cnt = lambda s: sum(1 for v in vs.values() if v["status"] == s)
        lat = f"{vs[vid]['date']}{' (archived)' if archived else ''}" if vid else "not measured yet"
        name = f"[{p['title']}](productions/{slug}/BRIEF.md)" if vid else p["title"]
        L.append(f"| {name} | {len(vs)} | {lat} | {cnt('measured')} | {cnt('queued')} | {cnt('gave_up')} |")
    L += ["", "## Waiting for a person", ""]
    asks = registry.get("questions") or {}
    if not asks and not extra:
        L.append("Nothing.")
    for vid, q in sorted(asks.items()):
        cands = ", ".join(f"`{c}`" for c in q.get("candidates") or [])
        L.append(f"- `{q['source_name']}` ({q['date']}): {q['reason']}" + (f" ({cands})" if cands else "") + ". "
                 f"Answer in `engine/productions/aliases.json`: `\"{vid}\": {{\"project\": \"<slug>\"}}` "
                 "(an existing slug for a new version, a new one for a new track) or `{\"ignore\": true}`.")
    for line in extra or []:
        L.append(f"- {line}")
    gave = [(s, k, v) for s, p in registry["projects"].items() for k, v in p["versions"].items() if v["status"] == "gave_up"]
    if gave:
        L += ["", "## Gave up after 3 tries", ""]
        L += [f"- {s}: `{v['source_name']}` ({v.get('why', 'unexpected_error')})" for s, k, v in sorted(gave)]
    jumps = []
    for slug, p in sorted(registry["projects"].items()):
        ms = measured(p["versions"])
        for (a, va), (b, vb) in zip(ms, ms[1:]):
            if va.get("bpm") and vb.get("bpm") and (abs(va["bpm"] - vb["bpm"]) > 4 or va.get("camelot") != vb.get("camelot")):
                jumps.append(f"- {slug}: `{vb['source_name']}` moves from {va['bpm']} BPM {va.get('camelot')} to "
                             f"{vb['bpm']} BPM {vb.get('camelot')}. It may be a different track; if so, answer with an alias.")
    if jumps:
        L += ["", "## Check these", ""] + jumps
    ign, other = listing_counts.get("ignored", 0), listing_counts.get("other_folders", 0)
    if ign or other:
        L += ["", "## Not read", ""]
        if ign:
            L.append(f"- {ign} file(s) of a kind the engine does not read (not audio, a text link or the sheet).")
        if other:
            L.append(f"- {other} file(s) in Music Production subfolders other than Archive.")
    L.append("")
    return "\n".join(L)
