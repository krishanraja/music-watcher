"""Stage B: their words and their references.

Words. The sheet ("Calvin and Krish - Spotify tracks") and text drops in Drive > Music Production > Inspiration go into
the one shared evidence log, taste/brain/evidence.jsonl, under the voice that said them (AGENTS.md: their words whole,
where and when said). Krish's brain counts both voices; Calvin's counts Calvin's. Rules:

- Sheet segments dated on or before BASELINE_THROUGH were read by hand on 2026-11-06 (taste/references.json is that
  read): they are recorded as seen and never written again.
- A new segment for a track and voice with no row yet is appended. Anything a person must judge becomes a question,
  asked once in the engine's PR: unattributed text, words about the speaker in the third person, new words on a track
  that voice already has a row for, a withdrawn row's track, and words holding any other link, an email or a phone
  number (never echoed).
- Auto tags come from engine/triggers.json (my read): strength 1, polarity +1, tagged_by, none under a negation.
- brain check runs before and after; only new problems undo the append.

References. Every Spotify track in a drop or on the sheet is a reference, measured once (SoundCloud within 6 s of
Spotify's length; otherwise left for a home computer) and listed in engine/references/index.csv. References carry
evidence ids, never words. Only drops feed a brain's measured layer (engine/references/<who>/tracks.csv, read through
policy "measured_extra"), with who = the Drive owner (or a krish/calvin word in the file name).

The engine's ledger of what it has read is engine/references/seen.jsonl (hashes, track ids and codes only).
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import re
from pathlib import Path

from . import measure as ms
from . import privacy
from .names import slugify
from .sources import Item, SourceError

BASELINE_THROUGH = "2026-11-16"
REFS = Path("engine/references")
EVIDENCE = Path("taste/brain/evidence.jsonl")
MAX_WORDS_CHARS = 600
MAX_REF_TRIES = 3
SPEAKER = re.compile(r"\b(Krish|Calvin)\b(?:\s*\(([^)]*)\))?\s*:", re.I)
NEGATION = re.compile(r"\b(not|no|don'?t|never|isn'?t|hate|dislike|too much|too many)\b", re.I)
THIRD = re.compile(r"\b(he|she)\b", re.I)
FIRST = re.compile(r"\b(i|i'm|i've|me|my|we|our|us)\b", re.I)
URL = re.compile(r"https?://[^\s\"'<>]+")
VOICES = ("krish", "calvin")


def _sha(words: str) -> str:
    return hashlib.sha256(" ".join(words.lower().split()).encode()).hexdigest()[:16]


def _date(s: str) -> str | None:
    s = (s or "").strip()
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%b %d %Y", "%B %d %Y"):
        try:
            return dt.datetime.strptime(s.replace(",", ""), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def _write_jsonl(p: Path, rows: list[dict]) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    p.write_text(text, encoding="utf-8")
    return text


# ---------------------------------------------------------------- parsing

def segments(comment: str, row_date: str | None = None) -> tuple[list[dict], str]:
    """Split a comment cell into speaker segments. Returns (segments, unattributed lead text)."""
    marks = list(SPEAKER.finditer(comment))
    lead = comment[: marks[0].start()].strip() if marks else comment.strip()
    first = next((d for d in (_date(m.group(2) or "") for m in marks) if d), None) or row_date
    out: dict[str, dict] = {}
    for i, m in enumerate(marks):
        words = comment[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(comment)].strip()
        if not words:
            continue
        who = m.group(1).lower()
        when = _date(m.group(2) or "") or first
        if who in out:  # one speaker twice in a cell: one row
            out[who]["text"] += " " + words
        else:
            out[who] = {"who": who, "when": when, "text": words}
    return list(out.values()), lead


def sheet_rows(text: str) -> list[dict]:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    head = [h.strip().lower() for h in rows[0]]
    col = lambda *keys: next((i for i, h in enumerate(head) if any(k in h for k in keys)), None)
    u, c, w = col("url", "link"), col("comment", "why", "reason", "note"), (head.index("who") if "who" in head else None)
    if u is None or c is None:
        return []
    out = []
    for n, r in enumerate(rows[1:], start=2):
        if len(r) <= max(u, c):
            continue
        out.append({"row": n, "url": r[u].strip(), "comment": r[c], "who": (r[w].strip().lower() if w is not None and len(r) > w else "")})
    return out


def tag(text: str, triggers: dict) -> list[dict]:
    if NEGATION.search(text):
        return []
    found = []
    low = text.lower()
    for phrase in sorted(triggers, key=len, reverse=True):
        for m in re.finditer(r"\b" + re.escape(phrase) + r"\b", low):
            if any(s < m.end() and m.start() < e for s, e, _ in found):
                continue
            found.append((m.start(), m.end(), triggers[phrase]))
    sigs, seen = [], set()
    for s, e, target in sorted(found):
        dim, slug = target.split("/")
        if (dim, slug) in seen:
            continue
        seen.add((dim, slug))
        sigs.append({"dim": dim, "slug": slug, "polarity": 1, "strength": 1, "quote": text[s:e],
                     "tagged_by": "engine (triggers)"})
    return sigs


def held(words: str, own_url: str = "") -> str | None:
    """Why words must go to a person before they can be published, or None."""
    if any(not ms.track_id(u) or ms.track_id(u) != ms.track_id(own_url) for u in URL.findall(words)):
        return "other_link"
    if privacy.scan(words):
        return "contact_details"
    if len(words) > MAX_WORDS_CHARS:
        return "too_long"
    return None


# ---------------------------------------------------------------- the stage

class Words:
    def __init__(self, engine, listing):
        self.e, self.listing = engine, listing
        self.root, self.cfg = engine.root, engine.cfg
        self.ledger = _jsonl(self.root / REFS / "seen.jsonl")
        self.seen = {(x["kind"], x["sha"]) for x in self.ledger}
        self.evidence = _jsonl(self.root / EVIDENCE)
        self.triggers = json.loads((self.root / "engine" / "triggers.json").read_text(encoding="utf-8"))["phrases"] \
            if (self.root / "engine" / "triggers.json").exists() else {}
        self.new_rows: list[dict] = []
        self.new_ledger: list[dict] = []
        self.questions: list[str] = []
        self.refs: dict[str, dict] = {}  # track id -> {who: set, sources: set, drop: bool}
        st = self.e.state.data
        self.first_seen = st.setdefault("first_seen", {})
        self.meta_cache = self.cfg.cache / "spotify"

    # ---- helpers
    def today(self, sha: str) -> str:
        if sha not in self.first_seen:
            self.first_seen[sha] = dt.date.today().isoformat()
            self.e.state.save()
        return self.first_seen[sha]

    def meta(self, tid: str) -> dict | None:
        f = self.meta_cache / f"{tid}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
        try:
            m = ms.spotify_meta(tid)
        except Exception:  # noqa: BLE001 - network: try again next run
            return None
        if not (m.get("title") and m.get("duration_s")):
            return None
        self.meta_cache.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(m, sort_keys=True), encoding="utf-8")
        return m

    def label(self, tid: str) -> str | None:
        for r in self.evidence:
            if ms.track_id(r.get("url", "")) == tid and r.get("track"):
                return r["track"]
        m = self.meta(tid)
        return f"{m['artists']} - {m['title']}" if m and m.get("artists") else (m["title"] if m else None)

    def has_row(self, tid: str, who: str) -> dict | None:
        return next((r for r in self.evidence + self.new_rows
                     if ms.track_id(r.get("url", "")) == tid and r.get("who") == who), None)

    def note(self, kind: str, sha: str, status: str, **kw) -> None:
        if (kind, sha) in self.seen:
            return
        self.seen.add((kind, sha))
        self.new_ledger.append({"kind": kind, "sha": sha, "status": status, **kw})

    def add_ref(self, tid: str, who: str | None, source: str, drop: bool = False) -> None:
        r = self.refs.setdefault(tid, {"who": set(), "sources": set(), "drop_who": set()})
        r["sources"].add(source)
        if who in VOICES:
            r["who"].add(who)
            if drop:
                r["drop_who"].add(who)

    def append(self, tid: str, who: str, when: str | None, text: str, where: str, sha: str) -> bool:
        track = self.label(tid)
        if track is None:
            return False  # Spotify unreachable: try again next run, nothing recorded
        base = slugify(track.split(" - ", 1)[-1]) + f"-{who}"
        ids = {r["id"] for r in self.evidence + self.new_rows}
        rid, n = base, 2
        while rid in ids:
            rid, n = f"{base}-{n}", n + 1
        self.new_rows.append({"id": rid, "who": who, "track": track, "url": ms.track_url(tid), "where": where,
                              "when": when or self.today(sha), "text": text, "signals": tag(text, self.triggers),
                              "withdrawn": False, "added_by": "engine"})
        return True

    def consider(self, kind: str, tid: str, who: str, when: str | None, text: str, where: str, own_url: str) -> None:
        sha = _sha(f"{tid}|{who}|{text}")
        if (kind, sha) in self.seen:
            return
        hold = held(text, own_url)
        existing = self.has_row(tid, who)
        if hold:
            self.note(kind, sha, "question", track=tid, who=who, why=hold)
            self.questions.append(f"{who.title()}'s words on track {tid} ({where.split(',')[0]}) hold "
                                  f"{hold.replace('_', ' ')}: a person must add them by hand.")
        elif (THIRD.search(text) and not FIRST.search(text)) or re.search(rf"\b{who}\b", text, re.I):
            self.note(kind, sha, "question", track=tid, who=who, why="reported_speech")
            self.questions.append(f"{who.title()}'s segment on track {tid} reads as reported speech (third person): "
                                  "add it by hand if they said it.")
        elif existing:
            why = "withdrawn_row" if existing.get("withdrawn") else "new_words_existing_row"
            self.note(kind, sha, "question", track=tid, who=who, why=why)
            self.questions.append(f"New words from {who.title()} on {existing.get('track')}, which already has row "
                                  f"`{existing['id']}`: a person decides whether they are a new row.")
        elif self.append(tid, who, when, text, where, sha):
            self.note(kind, sha, "appended", track=tid, who=who, id=self.new_rows[-1]["id"])

    # ---- sheet
    def sheet(self, item: Item) -> None:
        f = self.cfg.work_dir / f"{item.key}.csv"
        try:
            self.e.source.download(item, f)
            text = f.read_text(encoding="utf-8-sig")
        except (SourceError, OSError) as err:
            self.e.log(f"sheet: {privacy.why(str(err))}")
            return
        finally:
            f.unlink(missing_ok=True)
        title = Path(item.name).stem
        for r in sheet_rows(text):
            tid = ms.track_id(r["url"])
            if not tid:
                why = "playlist_link" if ms.PLAYLIST_RE.search(r["url"]) else "not_a_track_link"
                self.note("sheet", _sha(f"row|{r['url']}"), "skipped", why=why)
                continue
            dates = [d for d in (_date(m.group(2) or "") for m in SPEAKER.finditer(r["comment"])) if d]
            row_date = dates[0] if dates else None
            where = f"Google Sheet '{title}', row {r['row']} comment cell (cell author not recorded), read by the production engine"
            if r["who"] in VOICES:
                segs, lead = [{"who": r["who"], "when": row_date, "text": r["comment"].strip()}], ""
            else:
                segs, lead = segments(r["comment"], row_date)
            for s in segs:
                self.add_ref(tid, s["who"], "sheet")
                sha = _sha(f"{tid}|{s['who']}|{s['text']}")
                if s["when"] and s["when"] <= BASELINE_THROUGH:
                    self.note("sheet", sha, "baseline", track=tid, who=s["who"])
                    continue
                self.consider("sheet", tid, s["who"], s["when"], s["text"], where, r["url"])
            if lead:
                sha = _sha(f"{tid}|none|{lead}")
                if row_date and row_date <= BASELINE_THROUGH:
                    self.note("sheet", sha, "baseline", track=tid, who="none")
                elif ("sheet", sha) not in self.seen:
                    self.note("sheet", sha, "question", track=tid, who="none", why="no_speaker")
                    self.questions.append(f"Sheet row {r['row']} has words with no speaker: start them with "
                                          "'Krish:' or 'Calvin:', or add a Who column.")
            if not segs and not lead:
                self.add_ref(tid, None, "sheet")

    # ---- text drops
    def drop(self, item: Item) -> None:
        kind = "drop"
        sha = _sha(f"{item.key}|{item.sig}")
        prior = next((x for x in self.ledger if x["kind"] == kind and x["sha"] == sha), None)
        if prior:  # read before: its references still count
            for tid in prior.get("tracks", []):
                self.add_ref(tid, prior.get("who"), "drop", drop=True)
            return
        f = self.cfg.work_dir / f"{item.key}.txt"
        try:
            self.e.source.download(item, f)
            text = f.read_text(encoding="utf-8", errors="replace") + " " + item.name
        except (SourceError, OSError):
            return  # retried next run
        finally:
            f.unlink(missing_ok=True)
        who = item.who
        for w in VOICES:  # a name in the file name routes the reference (never the words)
            if re.search(rf"\b{w}\b", item.name, re.I):
                ref_who = w
                break
        else:
            ref_who = who
        urls = URL.findall(text)
        tids = list(dict.fromkeys(t for t in (ms.track_id(u) for u in urls) if t))
        if not tids:
            why = ("playlist_link" if any(ms.PLAYLIST_RE.search(u) for u in urls) else
                   "youtube_needs_home" if any(re.search(r"youtube\.com|youtu\.be", u) for u in urls) else
                   "private_link_needs_person" if any(privacy.scan(u) for u in urls) else
                   "not_a_track_link" if urls else "no_link")
            self.note(kind, sha, "skipped", who=ref_who, why=why)
            return
        for t in tids:
            self.add_ref(t, ref_who, "drop", drop=True)
        self.note(kind, sha, "read", who=ref_who, tracks=tids)
        words = URL.sub(" ", text.replace(item.name, " "))
        words = " ".join(words.split())
        if not words or who not in VOICES:
            return
        if len(tids) > 1:
            self.questions.append(f"A text drop by {who.title()} holds {len(tids)} track links and words: one link per "
                                  "file, so the words can be filed under the right track.")
            return
        when = item.btime[:10]
        where = f"Drive Music Production > Inspiration text file, uploaded by {who.title()}"
        segs, lead = segments(words, when) if SPEAKER.search(words) else ([{"who": who, "when": when, "text": words}], "")
        for s in segs:
            if s["who"] != who:
                self.questions.append(f"A text drop by {who.title()} quotes {s['who'].title()}: add it by hand if they said it.")
                continue
            self.consider("drop", tids[0], who, s["when"], s["text"], where, ms.track_url(tids[0]))
        if lead and segs:
            self.questions.append(f"A text drop by {who.title()} has words before its first speaker name.")

    # ---- references
    def measure_refs(self, budget: int) -> list[dict]:
        idx_path = self.root / REFS / "index.csv"
        old = {}
        if idx_path.exists():
            with open(idx_path, newline="", encoding="utf-8") as fh:
                old = {r["key"]: r for r in csv.DictReader(fh)}
        graphs = {}
        for who, rel in (("krish", "taste/graph/tracks.csv"), ("calvin", "taste/calvin/graph/tracks.csv")):
            p = self.root / rel
            if p.exists():
                with open(p, newline="", encoding="utf-8") as fh:
                    graphs[who] = {r["id"]: r for r in csv.DictReader(fh)}
        rows = []
        tries = self.e.state.data.setdefault("tries", {})
        for tid in sorted(self.refs):
            ref = self.refs[tid]
            m = self.meta(tid) or {}
            o = old.get(tid, {})
            row = {"key": tid, "title": m.get("title") or o.get("title", ""), "artists": m.get("artists") or o.get("artists", ""),
                   "link": ms.track_url(tid), "who": ";".join(sorted(ref["who"])), "sources": ";".join(sorted(ref["sources"])),
                   "spotify_duration_s": m.get("duration_s") or o.get("spotify_duration_s", ""),
                   "evidence": ";".join(sorted(r["id"] for r in self.evidence + self.new_rows
                                               if ms.track_id(r.get("url", "")) == tid))}
            card, where = self.find_card(tid)
            g = next((graphs[w][tid] for w in graphs if tid in graphs[w] and graphs[w][tid].get("measured") == "True"), None)
            if card is None and g is None and budget > 0 and tries.get(f"ref:{tid}", 0) < MAX_REF_TRIES and m:
                budget -= 1
                card, where = self.measure_one(tid, m)
            if card:
                row.update(status="measured", bpm=card.get("likely_project_bpm") or card.get("bpm"),
                           camelot=card.get("camelot"), key_name=card.get("key"), duration_s=round(card["duration"], 1),
                           stems=bool(card.get("stems_available")), card=where, why="")
            elif g:
                row.update(status="measured", bpm=g.get("bpm"), camelot=g.get("camelot"), key_name=g.get("key"),
                           duration_s=g.get("duration_s"), stems=g.get("stems"), card="graph tracks.csv", why="")
            else:
                gave = tries.get(f"ref:{tid}", 0) >= MAX_REF_TRIES
                why = self.e.state.data.get("why", {}).get(f"ref:{tid}", "") if gave else ""
                row.update(status=("left_for_home" if why == "no_soundcloud_match_within_6s" else "gave_up") if gave
                           else "queued", why=privacy.why(why) if why else "")
            row["_card"] = card
            rows.append(row)
        return rows

    def find_card(self, tid: str) -> tuple[dict | None, str]:
        for rel in (REFS / "cards", Path("taste/cards"), Path("taste/inspo/cards")):
            f = self.root / rel / f"{tid}.trackcard.json"
            if f.exists():
                return json.loads(f.read_text(encoding="utf-8")), str(rel / f.name)
        c = self.cfg.cache / "refcards" / f"{tid}.trackcard.json"
        if c.exists():
            return json.loads(c.read_text(encoding="utf-8")), str(REFS / "cards" / c.name)
        return None, ""

    def measure_one(self, tid: str, m: dict) -> tuple[dict | None, str]:
        st = self.e.state.data
        st.setdefault("tries", {})[f"ref:{tid}"] = st["tries"].get(f"ref:{tid}", 0) + 1
        self.e.state.save()
        why, card = "", None
        url = ms.soundcloud_match(self.cfg, m.get("artists") or "", m["title"], m["duration_s"])
        if not url:
            why = "no_soundcloud_match_within_6s"
        else:
            wav = ms.fetch_audio(self.cfg, url, self.cfg.work_dir / tid)
            if wav is None:
                why = "download_failed"
            else:
                try:
                    card, why = ms.analyze(self.cfg, wav, self.cfg.cache / "refcards")
                finally:
                    wav.unlink(missing_ok=True)
                if card and abs(card["duration"] - m["duration_s"]) > ms.LENGTH_TOLERANCE_S:
                    card, why = None, "no_soundcloud_match_within_6s"
        if card is None:
            st.setdefault("why", {})[f"ref:{tid}"] = privacy.why(why)
            self.e.state.save()
            self.e.log(f"reference {tid}: {privacy.why(why)}")
            return None, ""
        self.e.log(f"reference {tid}: measured")
        return card, str(REFS / "cards" / f"{tid}.trackcard.json")

    # ---- writing
    def write(self, rows: list[dict]) -> list[str]:
        touched = []
        refs = self.root / REFS
        refs.mkdir(parents=True, exist_ok=True)
        fields = ["key", "title", "artists", "link", "who", "sources", "status", "why", "bpm", "camelot", "key_name",
                  "duration_s", "spotify_duration_s", "stems", "card", "evidence"]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)
        (refs / "index.csv").write_text(buf.getvalue(), encoding="utf-8")
        touched.append(str(REFS / "index.csv"))
        for r in rows:  # cards measured by the engine: from the cache into the repository
            if r.get("card", "").startswith(str(REFS / "cards")):
                for ext in ("json", "md"):
                    src = self.cfg.cache / "refcards" / f"{r['key']}.trackcard.{ext}"
                    dst = self.root / REFS / "cards" / f"{r['key']}.trackcard.{ext}"
                    if src.exists() and not dst.exists():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                        touched.append(str(REFS / "cards" / dst.name))
        touched += self.write_feed(rows)
        ledger = sorted(self.ledger + self.new_ledger, key=lambda x: (x["kind"], x["sha"]))
        _write_jsonl(refs / "seen.jsonl", ledger)
        touched.append(str(REFS / "seen.jsonl"))
        return touched

    def write_feed(self, rows: list[dict]) -> list[str]:
        """Only drops feed a brain's measured layer; never a track already in that person's playlist graph."""
        touched = []
        graph_ids = {}
        for who, rel in (("krish", "taste/graph/tracks.csv"), ("calvin", "taste/calvin/graph/tracks.csv")):
            p = self.root / rel
            graph_ids[who] = set()
            if p.exists():
                with open(p, newline="", encoding="utf-8") as fh:
                    graph_ids[who] = {r["id"] for r in csv.DictReader(fh)}
        for who in VOICES:
            feed = []
            for r in rows:
                if who not in self.refs[r["key"]]["drop_who"] or r["key"] in graph_ids[who] or not r.get("_card"):
                    continue
                if not r.get("spotify_duration_s"):
                    continue
                feed.append(ms.feed_row(self.root, r["_card"], r["key"], r["title"], r["artists"],
                                        int(r["spotify_duration_s"]), "full (SoundCloud, length within 6 s of Spotify's)"))
            p = self.root / REFS / who / "tracks.csv"
            if not feed and not p.exists():
                continue
            fields = sorted({k for f in feed for k in f}) or ["id"]
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            for f in sorted(feed, key=lambda f: f["id"]):
                w.writerow(f)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(buf.getvalue(), encoding="utf-8")
            touched.append(str(REFS / who / "tracks.csv"))
        return touched

    def append_evidence(self) -> tuple[list[str], bool]:
        if not self.new_rows:
            return [], True
        from .. import brain as br
        path = self.root / EVIDENCE
        before_text = path.read_text(encoding="utf-8")
        brains = [self.root / "taste", self.root / "taste" / "calvin"]
        before = {str(b): set(br.check(br.load(b))) for b in brains if (b / "brain" / "policy.json").exists()}
        add = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in self.new_rows)
        path.write_text(before_text + ("" if before_text.endswith("\n") or not before_text else "\n") + add, encoding="utf-8")
        new_problems = []
        for b in brains:
            if str(b) in before:
                new_problems += sorted(set(br.check(br.load(b))) - before[str(b)])
        if new_problems:
            path.write_text(before_text, encoding="utf-8")
            self.e.log(f"evidence append undone: brain check found {len(new_problems)} new problem(s)")
            appended = {r["id"] for r in self.new_rows}
            self.new_ledger = [x for x in self.new_ledger if x.get("id") not in appended]
            self.new_rows = []
            return [], False
        return [str(EVIDENCE)], True


def words_stage(engine, listing):
    """Returns (paths touched, STATUS lines, notes for the commit message and PR body)."""
    w = Words(engine, listing)
    for it in listing.items:
        if it.kind == "sheet":
            w.sheet(it)
        elif it.kind == "text":
            w.drop(it)
    budget = max(0, engine.cfg.max_per_run - len(getattr(engine, "measured_now", [])))
    rows = w.measure_refs(budget)
    touched, ok = w.append_evidence()
    touched += w.write(rows)
    touched += render_brains(engine.root)
    status = list(w.questions)
    q = [r for r in rows if r["status"] in ("left_for_home", "gave_up")]
    if q:
        status.append(f"{len(q)} reference(s) not measured: " + ", ".join(
            f"{r['artists']} - {r['title']} ({r['status'].replace('_', ' ')})" for r in q))
    lines = []
    if w.new_rows:
        lines += ["", "## Words added to taste/brain/evidence.jsonl", ""]
        for r in w.new_rows:
            tags = ", ".join(f"{s['dim']}/{s['slug']} (\"{s['quote']}\")" for s in r["signals"])
            lines.append(f"- `{r['id']}` ({r['who'].title()}, {r['track']})" +
                         (f": auto tags, my read, confirm or retag: {tags}" if tags else ": no tags"))
    base = [x for x in w.new_ledger if x["status"] == "baseline" and x.get("who") in VOICES]
    if base:
        missing = sum(1 for x in base if not w.has_row(x["track"], x["who"]))
        lines += ["", f"{len(base)} sheet segment(s) dated on or before {BASELINE_THROUGH} were recorded as already read "
                  f"(the 2026-11-06 hand read); {missing} of them have no evidence row, as that read chose. "
                  "Add any of them by hand if they should count."]
    if w.questions:
        lines += ["", "## For a person", ""] + [f"- {x}" for x in w.questions]
    feeds = {who: sum(1 for t, r in w.refs.items() if who in r["drop_who"]) for who in VOICES}
    if feeds["calvin"]:
        lines += ["", "Calvin: your drops now count in your brain's measured layer next to your playlist, so the basis of "
                  "your open proposals can move (taste/calvin/APPROVED.md)."]
    if not ok:
        status.append("Words from the sheet or a drop were held back: brain check found a new problem.")
    return touched, status, {"lines": lines, "evidence": len(w.new_rows),
                             "references": sum(1 for r in rows if r["status"] == "measured")}


def render_brains(root: Path) -> list[str]:
    from .. import brain as br
    out = []
    for rel in ("taste", "taste/calvin"):
        d = root / rel
        if (d / "brain" / "policy.json").exists():
            br.write_views(br.load(d))
            out += [f"{rel}/APPROVED.md", f"{rel}/brain/PATTERNS.md"]
    return out
