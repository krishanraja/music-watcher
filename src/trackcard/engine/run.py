"""One engine run, and `plan` (the same classification without measuring or writing).

A run is a pure function of main's tree, the Drive listing, aliases.json and the worker's cache of measured cards:
with --publish the clone is reset to origin/main first, everything the engine owns is rewritten, and the difference is
one commit on the rolling branch (engine/updates) with one open PR. Nothing is decided from what an unmerged branch
says; measured cards survive in the cache (and are recovered from the open branch if the cache is lost).

Worker state (outside the clone): tries per version (written before each attempt, so a crash counts), the last failure
code, and whether the engine is paused (a PR closed without merging, or someone else's commit on its branch).
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import brief as bf
from . import names, privacy
from .config import Config
from .measure import measure_file
from .sources import Item, Listing, SourceError

MAX_TRIES = 3
AUDIO_SUFFIXES = {".wav", ".wave", ".aif", ".aiff", ".flac", ".mp3", ".m4a", ".ogg", ".opus"}
MAX_COMMITTED_BYTES = 5_000_000
PROD = Path("engine/productions")


def dumps(obj) -> str:
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------- worker state

class State:
    def __init__(self, path: Path):
        self.path = path
        self.data = {"tries": {}, "why": {}, "paused": None, "resume_after_pr": None}
        if path.exists():
            try:
                self.data.update(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                path.rename(path.with_suffix(f".corrupt-{int(time.time())}"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    def tries(self, vid: str) -> int:
        return int(self.data["tries"].get(vid, 0))


def journal(cfg: Config, msg: str, secrets: set[str] = frozenset()) -> None:
    cfg.journal.parent.mkdir(parents=True, exist_ok=True)
    line = time.strftime("%Y-%m-%dT%H:%M:%SZ ", time.gmtime()) + privacy.redact(msg, secrets)
    with cfg.journal.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


# ---------------------------------------------------------------- classification

def _read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    except json.JSONDecodeError:
        return default


def _base_fields(it_name: str, btime: str, alias: dict) -> dict:
    p = names.parse(it_name, btime)
    rec = {"source_name": it_name, "btime": btime, "date": p.date, "date_source": p.date_source, "version": p.version,
           "note": p.note, "format": p.ext, "lossless": p.lossless}
    if alias.get("date"):
        rec.update(date=alias["date"], date_source="alias")
    for k in ("note", "by"):
        if k in alias:
            rec[k] = alias[k]
    return rec


def _rev(vid: str) -> int:
    return int(vid.split("-r")[1]) if "-r" in vid else 1


@dataclass
class Plan:
    registry: dict
    rows: list[dict] = field(default_factory=list)  # for `engine plan`


def classify(listing: Listing, old: dict, aliases: dict) -> Plan:
    """Fold this listing into main's registry. Existing versions keep their project unless an alias moves them."""
    reg = {"schema_version": 1, "projects": {}, "questions": {}}
    by_key: dict[str, list[tuple[str, str, dict]]] = {}
    for slug, proj in (old.get("projects") or {}).items():
        reg["projects"][slug] = {"title": proj["title"], "versions": {}}
        for vid, v in proj["versions"].items():
            by_key.setdefault(vid.split("-r")[0], []).append((vid, slug, v))
    audio = [it for it in listing.items if it.kind == "audio"]
    present = {it.key: it for it in audio}
    plan = Plan(reg)

    def alias_for(vid: str, slug: str | None) -> dict:
        return aliases.get(vid) or (aliases.get(slug) if slug else None) or {}

    # 1. versions already on main: refresh what Drive says now, re-apply aliases
    for key, entries in by_key.items():
        it = present.get(key)
        for vid, slug, v in entries:
            a = alias_for(vid, slug)
            fresh = it and v.get("md5") == it.md5 and not (privacy.scan(it.name) or privacy.scan_contacts(Path(it.name).stem))
            name, btime = (it.name, it.btime) if fresh else (v["source_name"], v["btime"])
            rec = {**v, **_base_fields(name, btime, a)}
            rec["present"] = bool(it and v.get("md5") == it.md5)
            if it and rec["present"]:
                rec["folder"] = it.folder
            target = names.slugify(a["project"]) if a.get("project") else slug
            if a.get("ignore"):
                continue
            proj = reg["projects"].setdefault(target, {"title": a.get("title") or a.get("project") or v["source_name"],
                                                       "versions": {}})
            proj["versions"][vid] = rec
            plan.rows.append({"name": rec["source_name"], "key": vid, "who": rec.get("by"), "folder": rec.get("folder"),
                              "date": rec["date"], "date_source": rec["date_source"], "note": rec["note"],
                              "version": rec["version"], "decision": "known", "project": target,
                              "status": rec.get("status")})
    known_md5 = {v["md5"]: (vid, s) for s, p in reg["projects"].items() for vid, v in p["versions"].items() if v.get("md5")}

    # 2. new files and new content under a known id, in a fixed order
    for it in sorted(audio, key=lambda i: (i.btime, i.key)):
        olds = by_key.get(it.key, [])
        if any(v.get("md5") == it.md5 for _, _, v in olds):
            continue
        vid = it.key if not olds else f"{it.key}-r{max(_rev(v) for v, _, _ in olds) + 1}"
        if privacy.scan(it.name) or privacy.scan_contacts(Path(it.name).stem):
            reg["questions"][vid] = {"source_name": "(name withheld)", "date": it.btime[:10], "candidates": [],
                                     "reason": "the file name holds contact details or a link: rename it in Drive, "
                                               "or ignore it in aliases.json"}
            plan.rows.append({"name": "(name withheld)", "key": vid, "who": it.who, "folder": it.folder,
                              "date": it.btime[:10], "date_source": "upload", "note": "", "version": None,
                              "decision": "ask", "project": "", "reason": "name withheld"})
            continue
        p = names.parse(it.name, it.btime)
        a = alias_for(vid, p.slug)
        rec = {**_base_fields(it.name, it.btime, a), "folder": it.folder, "present": True, "md5": it.md5,
               "by": a.get("by") or p.by_hint or it.who, "status": "queued"}
        row = {"name": it.name, "key": vid, "who": rec["by"], "folder": it.folder, "date": rec["date"],
               "date_source": rec["date_source"], "note": rec["note"], "version": rec["version"]}
        if it.md5 and it.md5 in known_md5:
            same_vid, same_slug = known_md5[it.md5]
            reg["projects"][same_slug]["versions"][vid] = {**rec, "status": "copy_of", "copy_of": same_vid}
            plan.rows.append({**row, "decision": "copy", "project": same_slug})
            continue
        d = names.decide(p, vid, set(reg["projects"]), aliases)
        if d.kind == "ignore":
            plan.rows.append({**row, "decision": "ignored", "project": ""})
            continue
        if d.kind == "ask":
            reg["questions"][vid] = {"source_name": it.name, "date": rec["date"], "reason": d.reason,
                                     "candidates": list(d.candidates)}
            plan.rows.append({**row, "decision": "ask", "project": "", "reason": d.reason})
            continue
        proj = reg["projects"].setdefault(d.project, {"title": a.get("title") or a.get("project") or p.title or d.project,
                                                       "versions": {}})
        # the same bounce in another format: measure the lossless one, keep the other as an alternate
        twin = next((k for k, v in proj["versions"].items()
                     if (v["date"], v.get("note"), v.get("version")) == (rec["date"], rec["note"], rec["version"])
                     and v.get("status") not in ("copy_of", "alternate") and v.get("format") != rec["format"]), None)
        if twin and (proj["versions"][twin]["lossless"] or not rec["lossless"]):
            rec.update(status="alternate", alternate_of=twin)
        elif twin and rec["lossless"] and not proj["versions"][twin]["lossless"]:
            proj["versions"][twin].update(status="alternate", alternate_of=vid)
        proj["versions"][vid] = rec
        if it.md5:
            known_md5[it.md5] = (vid, d.project)
        plan.rows.append({**row, "decision": "new track" if d.kind == "new" else "new version",
                          "project": d.project, "status": rec["status"]})
    reg["projects"] = {s: p for s, p in reg["projects"].items() if p["versions"]}
    return plan


# ---------------------------------------------------------------- the run

@dataclass
class Result:
    code: int = 0
    measured: list[str] = field(default_factory=list)
    written: list[str] = field(default_factory=list)
    message: str = ""



def _sh(cmd: list[str], cwd: Path, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


class Engine:
    def __init__(self, cfg: Config, source, sh=_sh, measurer=measure_file, clock=time.monotonic):
        self.cfg, self.source, self.sh, self.measurer, self.clock = cfg, source, sh, measurer, clock
        self.state = State(cfg.state_file)
        self.root = cfg.clone
        self.main_md5: dict[str, str] = {}  # version id -> md5, as main's registry has it
        self.md5_of: dict[str, str] = {}

    # ---- helpers
    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        r = self.sh(["git", *args], self.root)
        if check and r.returncode != 0:
            raise RuntimeError(f"git {args[0]} failed")
        return r

    def secrets(self) -> set[str]:
        return self.source.raw_ids() | self.cfg.private_values() | {str(self.cfg.work_dir), str(self.cfg.state_dir)}

    def log(self, msg: str) -> None:
        journal(self.cfg, msg, self.secrets())

    @property
    def cards_dir(self) -> Path:
        return self.root / PROD / "cards"

    # ---- stages
    def card_for(self, vid: str, md5: str | None = None) -> dict | None:
        """The card measured from exactly this audio: a committed card only if main's registry has the same md5 for it,
        a cached one only if its md5 sidecar matches. A stale cache entry is removed (its audio was replaced)."""
        if md5 is None:
            md5 = self.md5_of.get(vid, "")
        f = self.cards_dir / f"{vid}.trackcard.json"
        if f.exists() and self.main_md5.get(vid) == md5:
            return json.loads(f.read_text(encoding="utf-8"))
        c = self.cfg.cache / "cards" / f"{vid}.trackcard.json"
        side = c.with_suffix("").with_suffix(".md5")
        if c.exists():
            if side.exists() and side.read_text().strip() == md5:
                return json.loads(c.read_text(encoding="utf-8"))
            for ext in ("trackcard.json", "trackcard.md", "md5"):
                (self.cfg.cache / "cards" / f"{vid}.{ext}").unlink(missing_ok=True)
            self.state.data["tries"].pop(vid, None)
            self.state.save()
        return None

    def recover_from_branch(self, vid: str, md5: str) -> None:
        """A card measured earlier whose PR is still open: take it back from the branch if the cache lost it, only when
        the branch's registry says it was measured from this same audio."""
        cache = self.cfg.cache / "cards"
        r = self.sh(["git", "show", f"origin/{self.cfg.branch}:{PROD}/registry.json"], self.root)
        try:
            reg = json.loads(r.stdout) if r.returncode == 0 else {}
        except json.JSONDecodeError:
            reg = {}
        if not any(p["versions"].get(vid, {}).get("md5") == md5 for p in (reg.get("projects") or {}).values()):
            return
        cache.mkdir(parents=True, exist_ok=True)
        (cache / f"{vid}.md5").write_text(md5)
        for ext in ("json", "md"):
            r = self.sh(["git", "show", f"origin/{self.cfg.branch}:{PROD}/cards/{vid}.trackcard.{ext}"], self.root)
            if r.returncode == 0 and r.stdout:
                cache.mkdir(parents=True, exist_ok=True)
                (cache / f"{vid}.trackcard.{ext}").write_text(r.stdout, encoding="utf-8")

    def measure_queue(self, reg: dict, items: dict[str, Item], aliases: dict, publish: bool) -> list[str]:
        start, done = self.clock(), []
        queue = []
        for slug, p in reg["projects"].items():
            for vid, v in p["versions"].items():
                if v["status"] != "queued":
                    continue
                self.md5_of[vid] = v.get("md5", "")
                if publish and self.card_for(vid) is None:
                    self.recover_from_branch(vid, v.get("md5", ""))
                if self.card_for(vid) is not None:
                    v["status"] = "measured"
                elif self.state.tries(vid) >= MAX_TRIES:
                    v.update(status="gave_up", why=privacy.why(self.state.data["why"].get(vid, "unexpected_error")))
                elif v.get("present") and vid.split("-r")[0] in items:
                    queue.append((v["btime"], vid, slug))
        queue.sort(reverse=True)  # newest bounce first
        for _, vid, slug in queue[: self.cfg.max_per_run]:
            if self.clock() - start > self.cfg.budget_s:
                self.log(f"budget reached; {vid} waits for the next run")
                break
            v = reg["projects"][slug]["versions"][vid]
            self.state.data["tries"][vid] = self.state.tries(vid) + 1
            self.state.save()  # before the attempt: a crash or kill still counts
            it = items[vid.split("-r")[0]]
            src = self.cfg.work_dir / f"{vid}{it.ext or '.audio'}"
            card, why = None, ""
            try:
                self.source.download(it, src)
                a = aliases.get(vid) or aliases.get(slug) or {}
                card, why = self.measurer(self.cfg, src, vid, self.cfg.cache / "cards", a.get("bpm"), a.get("key"))
            except SourceError as e:
                why = str(e)
            except Exception as e:  # noqa: BLE001 - one bad file must not stop the run
                self.log(f"{vid}: unexpected {type(e).__name__}: {e}")
                why = "unexpected_error"
            finally:
                src.unlink(missing_ok=True)
            if card is None:
                self.state.data["why"][vid] = privacy.why(why)
                self.state.save()
                self.log(f"{vid}: {privacy.why(why)} (try {self.state.tries(vid)} of {MAX_TRIES})")
                if self.state.tries(vid) >= MAX_TRIES:
                    v.update(status="gave_up", why=privacy.why(why))
                continue
            (self.cfg.cache / "cards" / f"{vid}.md5").write_text(v.get("md5", ""))
            v["status"] = "measured"
            done.append(vid)
            self.log(f"{vid}: measured")
        return done

    def write(self, reg: dict, listing: Listing, extra_status: list[str]) -> list[str]:
        """Rewrite everything the engine owns under engine/productions. Returns the paths written or removed."""
        touched: list[str] = []
        prod = self.root / PROD
        self.cards_dir.mkdir(parents=True, exist_ok=True)

        def put(rel: Path, text: str) -> None:
            f = self.root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            if not f.exists() or f.read_text(encoding="utf-8") != text:
                f.write_text(text, encoding="utf-8")
            touched.append(str(rel))

        for slug, p in reg["projects"].items():
            for vid, v in p["versions"].items():
                self.md5_of[vid] = v.get("md5", "")
                if v["status"] == "measured" and self.card_for(vid) is None:
                    v["status"] = "queued"  # its card was measured from audio that has since been replaced
                if v["status"] != "measured":
                    continue
                for ext in ("json", "md"):
                    rel = PROD / "cards" / f"{vid}.trackcard.{ext}"
                    cached = self.cfg.cache / "cards" / f"{vid}.trackcard.{ext}"
                    if not (self.root / rel).exists() and cached.exists():
                        put(rel, cached.read_text(encoding="utf-8"))
                card = self.card_for(vid)
                v.update(bpm=card.get("likely_project_bpm") or card.get("bpm"), camelot=card.get("camelot"),
                         stems=bool(card.get("stems_available")))
        put(PROD / "registry.json", dumps(reg))
        rules = brain_rules(self.root)
        refs = bf.reference_rows(self.root)
        from ..studio import ledger as lg
        from ..studio import targets as tg
        targets = tg.brain_targets(self.root)
        live = set()
        for slug, p in sorted(reg["projects"].items()):
            out = bf.project_brief(slug, p, self.cards_dir, rules, refs, studio_inputs(self.root, slug, targets))
            if out is None:
                continue
            md, data = out
            live.add(slug)
            put(PROD / slug / "BRIEF.md", md)
            put(PROD / slug / "brief.json", dumps(data))
        for d in prod.iterdir() if prod.exists() else []:
            if d.is_dir() and d.name != "cards" and d.name not in live:
                for f in ("BRIEF.md", "brief.json"):
                    if (d / f).exists():
                        (d / f).unlink()
                        touched.append(str(PROD / d.name / f))
        ears = []
        for slug in sorted(live):
            data = json.loads((self.root / PROD / slug / "brief.json").read_text(encoding="utf-8"))
            e = data.get("second_ear") or {}
            for q in e.get("questions") or []:
                ears.append(f"Ear-check, [{p_title(reg, slug)}](productions/{slug}/BRIEF.md): {q['text']}")
        put(Path("engine/STATUS.md"),
            bf.status_md(reg, {"ignored": listing.ignored, "other_folders": listing.other_folders}, extra_status + ears,
                         north_star=lg.score(reg, self.cards_dir, self.root)))
        return touched

    # ---- publish
    def prepare_clone(self) -> None:
        self.git("fetch", "-q", "--prune", "origin")
        self.git("checkout", "-q", "-B", self.cfg.branch, f"origin/{self.cfg.base}")
        self.git("reset", "-q", "--hard", f"origin/{self.cfg.base}")
        self.git("clean", "-q", "-fd", "--", "engine", "taste")

    def gh(self, *args: str) -> subprocess.CompletedProcess:
        return self.sh([*self.cfg.tool("gh"), *args], self.root)

    def last_pr(self) -> dict | None:
        r = self.gh("pr", "list", "--head", self.cfg.branch, "--state", "all", "--json",
                    "number,state,mergedAt,isCrossRepository", "--limit", "20")
        if r.returncode != 0:
            raise RuntimeError("gh pr list failed")
        prs = [p for p in json.loads(r.stdout or "[]") if not p.get("isCrossRepository")]  # never a fork's PR
        return max(prs, key=lambda p: p["number"]) if prs else None

    def publish(self, touched: list[str], title: str, body: str, message: str) -> int:
        if touched:
            self.git("add", "-A", "--", *sorted(set(touched)))
        staged = [l for l in self.git("diff", "--cached", "--name-only").stdout.splitlines() if l]
        if not staged:
            self.log("nothing differs from main")
            return 0
        for path in staged:
            f = self.root / path
            if Path(path).suffix.lower() in AUDIO_SUFFIXES or (f.exists() and f.stat().st_size > MAX_COMMITTED_BYTES):
                self.git("reset", "-q")
                self.log("refused: audio or an oversized file was staged")
                return 3
        added = "\n".join(l[1:] for l in self.git("diff", "--cached", "-U0").stdout.splitlines()
                          if l.startswith("+") and not l.startswith("+++"))
        hits = privacy.scan("\n".join([added, title, body, message]), self.secrets())
        if hits:
            self.git("reset", "-q")
            self.log("privacy gate refused the commit: " + ", ".join(sorted(set(hits))))
            return 3
        pr = self.last_pr()
        if pr and pr["state"] == "CLOSED" and not pr.get("mergedAt") and pr["number"] != self.state.data.get("resume_after_pr"):
            self.state.data["paused"] = {"why": "pr_closed_unmerged", "pr": pr["number"]}
            self.state.save()
            self.git("reset", "-q")
            self.log(f"paused: PR {pr['number']} was closed without merging; `trackcard engine resume` to go on")
            return 0
        remote = self.sh(["git", "rev-parse", "-q", "--verify", f"origin/{self.cfg.branch}"], self.root)
        remote_sha = remote.stdout.strip() if remote.returncode == 0 else ""
        if remote_sha and pr and pr["state"] == "OPEN":
            ident = self.git("var", "GIT_AUTHOR_IDENT", check=False).stdout
            me = ident[ident.find("<") + 1:ident.find(">")] if "<" in ident else ""
            authors = set(self.git("log", f"origin/{self.cfg.base}..origin/{self.cfg.branch}", "--format=%ae").stdout.split())
            if me and authors - {me}:
                self.state.data["paused"] = {"why": "foreign_commits", "pr": pr["number"]}
                self.state.save()
                self.git("reset", "-q")
                self.log("paused: someone else committed to the engine's branch; merge or close its PR, then resume")
                return 0
        self.git("commit", "-q", "-m", message)
        same = bool(remote_sha) and \
            self.git("rev-parse", "HEAD^{tree}").stdout == self.git("rev-parse", f"{remote_sha}^{{tree}}").stdout
        is_open = bool(pr and pr["state"] == "OPEN")
        if same and is_open:
            self.log("the open PR already holds this")
            return 0
        if not same:
            lease = f"--force-with-lease={self.cfg.branch}:{remote_sha}"
            if self.sh(["git", "push", "-q", lease, "origin", f"HEAD:{self.cfg.branch}"], self.root).returncode != 0:
                self.log("push refused; retried next run")
                return 1
        if is_open:
            r = self.gh("pr", "edit", str(pr["number"]), "--title", title, "--body", body)
        else:
            r = self.gh("pr", "create", "--base", self.cfg.base, "--head", self.cfg.branch, "--title", title, "--body", body)
        if r.returncode != 0:
            self.log("gh could not open or edit the PR; retried next run")
            return 1
        return 0

    # ---- main
    def run(self, publish: bool = False, words=None) -> Result:
        res = Result()
        if publish and self.state.data.get("paused"):
            self.log(f"paused ({self.state.data['paused']['why']}); nothing done")
            return res
        if publish:
            self.prepare_clone()
        self.cfg.work_dir.mkdir(parents=True, exist_ok=True)
        for f in self.cfg.work_dir.iterdir():  # audio left by a killed run
            if f.is_file():
                f.unlink()
        try:
            listing = self.source.list()
        except SourceError as e:
            self.log(f"listing stopped: {privacy.why(str(e))}")
            res.code = 1
            return res
        old = _read_json(self.root / PROD / "registry.json", {})
        self.main_md5 = {vid: v.get("md5", "") for p in (old.get("projects") or {}).values() for vid, v in p["versions"].items()}
        aliases = _read_json(self.root / PROD / "aliases.json", {})
        plan = classify(listing, old, aliases)
        items = {it.key: it for it in listing.items if it.kind == "audio"}
        res.measured = self.measure_queue(plan.registry, items, aliases, publish)
        self.measured_now = res.measured
        extra, touched_words, notes = [], [], {}
        if words is not None:
            touched_words, extra, notes = words(self, listing)
        res.written = self.write(plan.registry, listing, extra) + touched_words
        if publish:
            title = "engine: productions and references measured"
            body = pr_body(old, plan.registry, notes)
            message = commit_message(old, plan.registry, notes)
            res.code = self.publish(res.written, title, body, message)
        return res


# ---------------------------------------------------------------- texts for git and GitHub (fixed text + counts)

def _new_versions(old: dict, new: dict) -> list[tuple[str, str, dict]]:
    seen = {vid for p in (old.get("projects") or {}).values() for vid, v in p["versions"].items() if v["status"] == "measured"}
    return [(s, vid, v) for s, p in sorted(new["projects"].items()) for vid, v in bf.ordered(p["versions"])
            if v["status"] == "measured" and vid not in seen]


def commit_message(old: dict, new: dict, notes: dict) -> str:
    nv = _new_versions(old, new)
    lines = [f"engine: {len(nv)} version(s) measured, {notes.get('references', 0)} reference(s), "
             f"{notes.get('evidence', 0)} evidence row(s)", ""]
    lines += [f"- {s}: {v['date']}{' ' + v['note'] if v.get('note') else ''}" for s, _, v in nv]
    lines += ["", "Written by the production engine (trackcard engine run) on the worker."]
    return "\n".join(lines) + "\n"


def pr_body(old: dict, new: dict, notes: dict) -> str:
    nv = _new_versions(old, new)
    old_slugs = set((old.get("projects") or {}))
    L = ["The production engine's rolling update: bounces from Drive's Music Production folder measured by trackcard, "
         "with one brief per project in `engine/productions/<project>/BRIEF.md`, and what waits for a person in "
         "`engine/STATUS.md`. This PR is rebuilt from main on every run until it is merged; closing it without merging "
         "pauses the engine until `trackcard engine resume` runs on the worker.", "",
         "## New since main", ""]
    if not nv and not notes.get("lines"):
        L.append("Nothing measured yet; see STATUS for the queue.")
    for s, vid, v in nv:
        tag = "new track" if s not in old_slugs else "new version"
        L.append(f"- {tag}: **{new['projects'][s]['title']}** {v['date']}{' (' + v['note'] + ')' if v.get('note') else ''}, "
                 f"`{v['source_name']}`")
    L += notes.get("lines", [])
    q = len(new.get("questions") or {})
    if q:
        L += ["", f"{q} file(s) need a person to say which project they belong to (engine/STATUS.md)."]
    L += ["", "No audio, Drive ids or email addresses are committed: the engine's privacy gate checked this diff.", "",
          "Generated by the production engine on the worker."]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- the Studio's committed inputs (read only)

def p_title(reg: dict, slug: str) -> str:
    return reg["projects"][slug]["title"]


def studio_inputs(root: Path, slug: str, targets: dict) -> dict:
    """What sessions recorded for a project (engine/STUDIO.md): picks, Suno second-ear comparisons, measured twins."""
    from ..studio import ledger as lg
    d = root / PROD / slug
    ears = {f.stem: _read_json(f, None) for f in sorted((d / "ear").glob("*.json"))} if (d / "ear").is_dir() else {}
    twins = [_read_json(f, None) for f in sorted((d / "twins").glob("*.json"))] if (d / "twins").is_dir() else []
    return {"clone": root, "targets": targets, "ledger": lg.read(d / "moves.jsonl"),
            "ears": {k: v for k, v in ears.items() if v}, "twins": [t for t in twins if t]}


# ---------------------------------------------------------------- brains (read only)

def brain_rules(root: Path) -> list[dict]:
    from .. import brain as br
    out = []
    for who, rel in (("krish", "taste"), ("calvin", "taste/calvin")):
        d = root / rel
        if not (d / "brain" / "policy.json").exists():
            continue
        b = br.load(d)
        out.append({"brain": who, "decided_by": br.decider(b), "approved_md": f"{rel}/APPROVED.md",
                    "claims": [{"id": c["id"], "text": c["text"]} for c in b.claims if c["status"] == "accepted"]})
    return out


@contextlib.contextmanager
def locked(cfg: Config):
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    with open(cfg.state_dir / "engine.lock", "w") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("another engine run holds the lock") from None
        yield


def plan_rows(cfg: Config, source, clone: Path) -> tuple[list[dict], Listing]:
    listing = source.list()
    old = _read_json(clone / PROD / "registry.json", {})
    aliases = _read_json(clone / PROD / "aliases.json", {})
    return classify(listing, old, aliases).rows, listing


def resume(cfg: Config) -> str:
    st = State(cfg.state_file)
    p = st.data.get("paused")
    if not p:
        return "not paused"
    st.data["resume_after_pr"] = p.get("pr")
    st.data["paused"] = None
    st.save()
    return f"resumed (past PR {p.get('pr')})"


