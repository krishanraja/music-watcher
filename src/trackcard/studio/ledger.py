"""What people picked, and which pick closed which gap.

engine/productions/<slug>/moves.jsonl holds one row per pick a person made from a Studio move: which move, on which
version's brief, for which gap, what was picked (a public catalog id for Splice and Epidemic; only a 12-character hash
for anything in Suno, whose ids point at private songs), who chose it and when. The engine reads it on its next run and
credits a closed gap to the pick that was made for it on an earlier version.

The North Star (Krish, 2026-11-24): gaps closed per bounce, counted from the version diffs, with the share a Studio pick
closed.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

from ..engine import brief as bf
from ..engine import privacy

PROVIDERS = {"splice", "epidemic", "suno", "spotify", "none"}
VOICES = ("krish", "calvin")
UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
HASH = re.compile(r"^[0-9a-f]{12}$")


class LedgerError(ValueError):
    pass


def private_hash(value: str) -> str:
    """A Suno clip id (or any private id) as the 12 characters the ledger keeps."""
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def validate(row: dict) -> dict:
    need = {"move", "kind", "version", "pick", "who", "on"}
    if missing := need - set(row):
        raise LedgerError(f"missing: {', '.join(sorted(missing))}")
    extra = set(row) - need - {"gap", "credits", "note"}
    if extra:
        raise LedgerError(f"unknown field(s): {', '.join(sorted(extra))}")
    if row["who"] not in VOICES:
        raise LedgerError("who is krish or calvin")
    try:
        dt.date.fromisoformat(row["on"])
    except (TypeError, ValueError):
        raise LedgerError("on is a date, YYYY-MM-DD") from None
    p = row["pick"]
    if not isinstance(p, dict) or p.get("provider") not in PROVIDERS:
        raise LedgerError(f"pick.provider is one of {', '.join(sorted(PROVIDERS))}")
    if p["provider"] == "suno":
        if "id" in p or not HASH.match(p.get("hash", "")):
            raise LedgerError("a Suno pick keeps only a 12-character hash of its id, never the id")
    elif p["provider"] in ("splice", "epidemic"):
        if not UUID.match(p.get("id", "")):
            raise LedgerError(f"a {p['provider']} pick needs its catalog id (a UUID)")
    if set(p) - {"provider", "id", "hash", "title"}:
        raise LedgerError("pick holds provider, id or hash, and an optional title only")
    g = row.get("gap")
    if g is not None and (not isinstance(g, dict) or set(g) - {"rule", "layer", "bars"} or not g.get("layer")):
        raise LedgerError("gap is {rule, layer, bars} with a layer")
    if row.get("credits") is not None and not isinstance(row["credits"], (int, float)):
        raise LedgerError("credits is a number")
    text = json.dumps(row, ensure_ascii=False)
    if hits := privacy.scan(text):
        raise LedgerError("refused by the privacy gate: " + ", ".join(sorted(set(hits))))
    return row


def path_for(clone: Path, slug: str) -> Path:
    return Path(clone) / "engine" / "productions" / slug / "moves.jsonl"


def read(path: Path) -> list[dict]:
    """Valid rows only: a broken or merge-conflicted line is skipped (and reported by `bad_lines`), never fatal."""
    return [r for r in _rows(path) if r is not None]


def bad_lines(path: Path) -> int:
    return sum(1 for r in _rows(path) if r is None)


def _rows(path: Path) -> list[dict | None]:
    if not path.exists():
        return []
    out = []
    for l in path.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        try:
            r = json.loads(l)
            out.append(validate(r) if isinstance(r, dict) else None)
        except (json.JSONDecodeError, LedgerError, TypeError, KeyError):
            out.append(None)
    return out


def append(path: Path, row: dict) -> bool:
    """Add a validated row; False when the same move already has the same pick (nothing written)."""
    validate(row)
    rows = read(path)
    same = lambda r: r["move"] == row["move"] and r["pick"] == row["pick"] and r["who"] == row["who"]
    if any(same(r) for r in rows):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return True


def credit(closed: list[dict], rows: list[dict], earlier: set[str]) -> list[dict]:
    """closed gaps (from the diff) with closed_by: the picks made on an earlier version for the same layer and bars."""
    out = []
    for g in closed:
        by = []
        for r in rows:
            rg = r.get("gap") or {}
            if r.get("version") not in earlier or rg.get("layer") != g.get("layer") or r["pick"]["provider"] == "none":
                continue
            if rg.get("rule") and g.get("rule") and rg["rule"] != g["rule"]:
                continue
            if rg.get("bars") and g.get("bars") and not bf._overlap({"bars": rg["bars"]}, {"bars": g["bars"]}):
                continue
            by.append({"move": r["move"], "provider": r["pick"]["provider"], "who": r["who"], "on": r["on"]})
        out.append({**g, "closed_by": by})
    return out


def score(registry: dict, cards_dir: Path, clone: Path) -> dict:
    """The North Star: gaps closed per bounce. A bounce counts when it and the version before it were both measured
    with stems (only then are gaps compared); a closed gap counts as a Studio close when a pick was made for it."""
    by_project, bounces, closed, studio = {}, 0, 0, 0
    for slug, p in sorted((registry.get("projects") or {}).items()):
        ms = [k for k, _ in bf.measured(p["versions"])]
        rows = read(path_for(clone, slug))
        pb = pc = ps = 0
        for i in range(1, len(ms)):
            files = [Path(cards_dir) / f"{v}.trackcard.json" for v in ms[i - 1:i + 1]]
            if not all(f.exists() for f in files):
                continue
            a, b = (json.loads(f.read_text(encoding="utf-8")) for f in files)
            if not (a.get("stems_available") and b.get("stems_available")):
                continue
            ch = bf.gap_changes(a.get("brief") or [], b.get("brief") or [])
            cl = credit(ch["closed"], rows, set(ms[:i]))
            pb += 1
            pc += len(cl)
            ps += sum(1 for g in cl if g["closed_by"])
        by_project[slug] = {"bounces": pb, "gaps_closed": pc, "studio_closed": ps}
        bounces, closed, studio = bounces + pb, closed + pc, studio + ps
    return {"metric": "gaps closed per bounce", "bounces": bounces, "gaps_closed": closed, "studio_closed": studio,
            "per_bounce": round(closed / bounces, 2) if bounces else None, "by_project": by_project}
