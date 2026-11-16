"""Stage B: the sheet and text drops into the shared evidence log, references, and the brain feed."""
import csv
import io
import json
import shutil

import pytest

from engine_helpers import CALVIN, KRISH, REPO, STRANGER, FakeMeasurer, all_text, card, entry, fake_id, make_cfg, make_clone
from trackcard import brain as br
from trackcard.engine import measure as ms
from trackcard.engine.run import Engine
from trackcard.engine.sources import FixtureSource
from trackcard.engine.words import segments, tag, words_stage

T_NEW = "1aNewTrackAAAAAAAAAAAA"  # 22-character Spotify ids, invented
T_OLD = "331bJRuzgiksWvFiuVKhmH"  # On The Ground: already has a Krish row and a Calvin row in the real log
T_DROP = "2bDropTrackBBBBBBBBBBB"
T_GRAPH = "3EBHcU11daLLlDIUc6jHfB"  # in Krish's playlist graph
SHEET = "Calvin and Krish - Spotify tracks"


def sheet(*rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Spotify URL", "Comments"])
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


BASE_ROWS = [
    (f"https://open.spotify.com/track/{T_OLD}", "Krish (24 Mar 2026): Digging that growly bass. Calvin: Nice chops."),
    ("https://open.spotify.com/playlist/37i9dQZF1E8PL8GTxPd38U", "Krish (12 Jun 2026): Playlist, not a track."),
]


@pytest.fixture
def env(tmp_path, monkeypatch):
    clone = make_clone(tmp_path)
    shutil.copytree(REPO / "engine", clone / "engine", ignore=shutil.ignore_patterns("productions", "references"))
    cfg = make_cfg(tmp_path, clone, max_per_run=10)
    metas = {T_NEW: ("New Song", "Artist A", 240), T_OLD: ("On The Ground", "oskar med k", 300),
             T_DROP: ("Dropped Song", "Artist B", 250), T_GRAPH: ("Need You", "Flight Facilities", 201)}
    monkeypatch.setattr(ms, "spotify_meta", lambda tid: dict(zip(("title", "artists", "duration_s"), metas[tid])))
    monkeypatch.setattr(ms, "soundcloud_match", lambda cfg, a, t, s: f"https://soundcloud.com/x/{t.replace(' ', '-')}")

    def fetch(cfg, url, stem):
        stem.parent.mkdir(parents=True, exist_ok=True)
        stem.with_suffix(".wav").write_bytes(b"RIFF")
        return stem.with_suffix(".wav")

    def analyze(cfg, wav, out, bpm=None, key=None):
        tid = wav.stem
        c = card(tid, duration=float(next(m[2] for k, m in metas.items() if k == tid)))
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{tid}.trackcard.json").write_text(json.dumps(c))
        (out / f"{tid}.trackcard.md").write_text(f"# Track card: {tid}.wav\n")
        return c, ""

    monkeypatch.setattr(ms, "fetch_audio", fetch)
    monkeypatch.setattr(ms, "analyze", analyze)
    return cfg, tmp_path


def run(cfg, rows=(), drops=()):
    insp, files = [], {}
    if rows is not None:
        e = entry("sheet", f"{SHEET}.csv", owner=KRISH, mime="text/csv", btime="2026-11-06T09:29:10Z")
        insp.append(e)
        files[e["ID"]] = {"text": sheet(*BASE_ROWS, *rows)}
    for i, (name, owner, text) in enumerate(drops):
        e = entry(f"drop{i}", name, owner=owner, mime="text/plain", btime="2026-11-20T10:00:00Z")
        insp.append(e)
        files[e["ID"]] = {"text": text}
    eng = Engine(cfg, FixtureSource(cfg, {"productions": [], "inspiration": insp, "files": files}), measurer=FakeMeasurer())
    return eng.run(words=words_stage)


def evidence(cfg):
    return [json.loads(l) for l in (cfg.clone / "taste/brain/evidence.jsonl").read_text().splitlines() if l.strip()]


def test_segments_split_and_merge():
    segs, lead = segments("Shared first. Krish (24 Oct 2026): The pads. Calvin (on both): Organic. Krish: and the bass.")
    assert lead == "Shared first."
    assert segs == [{"who": "krish", "when": "2026-10-24", "text": "The pads. and the bass."},
                    {"who": "calvin", "when": "2026-10-24", "text": "Organic."}]


def test_tag_longest_match_strength_one_and_negation():
    t = json.loads((REPO / "engine/triggers.json").read_text())["phrases"]
    sigs = tag("Very organic sound and melodic percs", t)
    assert [(s["slug"], s["quote"], s["strength"]) for s in sigs] == [
        ("organic_textures", "organic sound", 1), ("melodic_percussion", "melodic percs", 1)]
    assert tag("not a fan of the panning", t) == []
    vocab = json.loads((REPO / "taste/brain/vocab.json").read_text())["dimensions"]
    for target in t.values():
        dim, slug = target.split("/")
        assert slug in vocab[dim], target


def test_history_is_a_baseline_and_writes_no_evidence(env):
    cfg, _ = env
    n = len(evidence(cfg))
    run(cfg)
    assert len(evidence(cfg)) == n
    ledger = [json.loads(l) for l in (cfg.clone / "engine/references/seen.jsonl").read_text().splitlines()]
    assert {x["status"] for x in ledger} == {"baseline", "skipped"}
    assert any(x.get("why") == "playlist_link" for x in ledger)


def test_new_two_voice_row_appends_two_rows_and_checks_clean(env):
    cfg, _ = env
    n = len(evidence(cfg))
    run(cfg, [(f"https://open.spotify.com/track/{T_NEW}?si=abc123",
               "Krish (20 Nov 2026): I love the growly bass and the panning. Calvin: Big tune, lush chords!")])
    ev = evidence(cfg)
    new = ev[n:]
    assert [(r["id"], r["who"], r["when"]) for r in new] == [("new-song-krish", "krish", "2026-11-20"),
                                                             ("new-song-calvin", "calvin", "2026-11-20")]
    assert new[0]["url"] == f"https://open.spotify.com/track/{T_NEW}" and new[0]["track"] == "Artist A - New Song"
    for r in new:
        assert all(s["quote"] in r["text"] and s["strength"] == 1 for s in r["signals"])
        assert r["added_by"] == "engine" and r["withdrawn"] is False
    assert br.check(br.load(cfg.clone / "taste")) == [] and br.check(br.load(cfg.clone / "taste/calvin")) == []
    # the references carry ids, never words
    refs = "\n".join(p.read_text() for p in (cfg.clone / "engine/references").rglob("*") if p.is_file())
    assert "growly" not in refs and "new-song-krish" in refs


def test_existing_voice_reported_speech_links_and_contacts_become_questions(env):
    cfg, _ = env
    n = len(evidence(cfg))
    res = run(cfg, [
        (f"https://open.spotify.com/intl-de/track/{T_OLD}", "Krish (20 Nov 2026): Still love it."),
        (f"https://open.spotify.com/track/{T_NEW}",
         "Calvin (20 Nov 2026): Likes how he chops the vocals. Krish: bounce at https://drive.google.com/file/d/1Xyz/view"),
        (f"https://open.spotify.com/track/{T_DROP}", "Krish (21 Nov 2026): call me on +44 7700 900123"),
    ])
    assert len(evidence(cfg)) == n
    status = (cfg.clone / "engine/STATUS.md").read_text()
    assert "already has row `on-the-ground-krish`" in status and "reported speech" in status
    text = all_text(cfg.clone / "engine") + all_text(cfg.clone / "taste")
    assert "drive.google.com/file/d/1Xyz" not in text and "7700" not in text


def test_withdrawn_rows_never_return(env):
    cfg, _ = env
    p = cfg.clone / "taste/brain/evidence.jsonl"
    rows = evidence(cfg)
    rows.append({"id": "new-song-krish", "who": "krish", "track": "Artist A - New Song",
                 "url": f"https://open.spotify.com/track/{T_NEW}", "where": "chat", "when": "2026-11-18",
                 "text": "growly bass", "signals": [], "withdrawn": True})
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    run(cfg, [(f"https://open.spotify.com/track/{T_NEW}", "Krish (20 Nov 2026): growly bass again")])
    assert len(evidence(cfg)) == len(rows)


def test_drop_words_feed_and_brain_extra(env):
    cfg, _ = env
    n = len(evidence(cfg))
    run(cfg, drops=[("pick.txt", KRISH, f"https://open.spotify.com/track/{T_DROP} the crisp beats on this"),
                    ("calvin likes.txt", KRISH, f"https://open.spotify.com/track/{T_NEW}"),
                    ("graph.txt", KRISH, f"https://open.spotify.com/track/{T_GRAPH}"),
                    ("who.txt", STRANGER, f"https://open.spotify.com/track/{T_GRAPH}")])
    new = evidence(cfg)[n:]
    assert [(r["who"], r["text"]) for r in new] == [("krish", "the crisp beats on this")]
    assert new[0]["signals"][0]["slug"] == "crisp_drums"
    feed_k = list(csv.DictReader((cfg.clone / "engine/references/krish/tracks.csv").open()))
    feed_c = list(csv.DictReader((cfg.clone / "engine/references/calvin/tracks.csv").open()))
    assert [r["id"] for r in feed_k] == [T_DROP]  # the graph track counts once, through the playlist
    assert [r["id"] for r in feed_c] == [T_NEW]  # a name in the file name routes the reference
    kb = br.load(cfg.clone / "taste")
    assert sum(1 for t in kb.tracks if t.get("extra") == "True") == 1 and br.has_extra(kb)
    assert br.measured_signals(next(t for t in kb.tracks if t["id"] == T_DROP))
    idx = {r["key"]: r for r in csv.DictReader((cfg.clone / "engine/references/index.csv").open())}
    assert idx[T_DROP]["status"] == "measured" and idx[T_GRAPH]["card"] == "graph tracks.csv"
    for s in (KRISH, STRANGER, CALVIN, fake_id("drop0")):
        assert s not in all_text(cfg.clone / "engine")


def test_dated_extras_leave_the_trend_alone(env):
    cfg, _ = env
    before = br.recount(br.load(cfg.clone / "taste/calvin"))
    run(cfg, drops=[("x.txt", CALVIN, f"https://open.spotify.com/track/{T_DROP}")])
    after = br.recount(br.load(cfg.clone / "taste/calvin"))
    assert {k: v["trend"] for k, v in before.items()} == {k: v["trend"] for k, v in after.items() if k in before}


def test_second_run_is_byte_identical(env):
    cfg, _ = env
    rows = [(f"https://open.spotify.com/track/{T_NEW}", "Krish (20 Nov 2026): I love the growly bass.")]
    drops = [("pick.txt", KRISH, f"https://open.spotify.com/track/{T_DROP}")]
    run(cfg, rows, drops)
    snap = {p: p.read_bytes() for p in cfg.clone.rglob("*") if p.is_file()}
    run(cfg, rows, drops)
    assert snap == {p: p.read_bytes() for p in cfg.clone.rglob("*") if p.is_file()}


def test_unknown_link_kinds_are_logged_with_codes(env):
    cfg, _ = env
    run(cfg, drops=[("yt.txt", KRISH, "https://youtu.be/abc"), ("pl.txt", KRISH, "https://open.spotify.com/playlist/xyz"),
                    ("sc.txt", KRISH, "https://soundcloud.com/a/b/s-SECRET1"), ("none.txt", KRISH, "just words")])
    ledger = [json.loads(l) for l in (cfg.clone / "engine/references/seen.jsonl").read_text().splitlines()]
    whys = sorted(x["why"] for x in ledger if x["kind"] == "drop")
    assert whys == ["no_link", "playlist_link", "private_link_needs_person", "youtube_needs_home"]
    assert "SECRET1" not in all_text(cfg.clone / "engine")
