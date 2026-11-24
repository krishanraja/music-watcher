"""The Studio (trackcard.studio): moves, the second ear, pro twins, drop on the cut, the ledger and the North Star,
revealed taste, and the brief v2 the engine writes with them. Every id here is invented."""
import copy
import json
import math

import pytest
from click.testing import CliRunner

from engine_helpers import REPO, FakeMeasurer, all_text, card, fake_id, make_cfg, make_clone
from test_engine_run import engine, listing
from engine_helpers import files_for
from trackcard.cli import main
from trackcard.engine import privacy
from trackcard.engine.sources import key_of
from trackcard.studio import cut, grid, ledger, moves, revealed, second_ear, targets, twin

SPLICE_UUID = "48bd0062-a380-4d47-b0e1-e4d8f45b0ee5"
EPI_UUID = "717184a7-d5e3-445b-ab12-8953bd897c0b"
SUNO_CLIP = "5c0ffee0-1234-4abc-8def-0123456789ab"


@pytest.fixture
def env(tmp_path):
    clone = make_clone(tmp_path)
    cfg = make_cfg(tmp_path, clone, max_per_run=10)
    data = listing()
    data["files"] = files_for(data, tmp_path)
    return cfg, data, tmp_path


def tc(**kw):
    """The template card (126 BPM, bar 1 at 0.25 s, G minor or D# major, main drop at bar 58)."""
    c = card("v1", **kw)
    return c


# ---------------------------------------------------------------- the grid

def test_grid_matches_the_cards_own_bar_numbers():
    c = tc()
    bpm, b1 = grid.project_bpm(c), grid.bar1(c)
    for d in c["drops"]:
        assert abs(grid.time_of(d["bar"], b1, bpm) - d["time"]) < 0.02
        assert grid.bar_at(d["time"], b1, bpm) == d["bar"]


# ---------------------------------------------------------------- drop on the cut

def test_cut_lands_a_bar_33_drop_on_a_12_4_s_reveal_to_the_millisecond():
    c = tc()
    bl = grid.bar_len(126)
    t33 = grid.time_of(33, 0.25, 126)
    c["drops"] = [{"bar": 33, "time": t33, "main": True}]
    out = cut.edit_input(c, 30, 12.4, EPI_UUID)
    r = out["args"]["input"]["requiredRegionsAtOffsets"][0]
    assert out["args"]["id"] == EPI_UUID and out["args"]["input"]["targetDurationMs"] == 30000
    assert out["args"]["input"]["forceDuration"] is True
    assert abs(r["offsetMsInEdit"] + (round(t33 * 1000) - r["startMs"]) - 12400) <= 1  # the drop sits on the reveal
    assert abs((round(t33 * 1000) - r["startMs"]) - 4 * bl * 1000) <= 1  # four whole bars of build kept
    assert r["offsetMsInEdit"] + (r["endMs"] - r["startMs"]) <= 30000  # the region fits in the edit
    assert set(out["args"]["input"]) <= {"targetDurationMs", "downloadAudioFormat", "forceDuration", "loopable",
                                         "maxResults", "preferenceRegions", "requiredRegionsAtOffsets", "skipStems"}


def test_cut_shrinks_the_build_to_fit_an_early_hit_and_refuses_impossible_edits():
    c = tc()
    out = cut.edit_input(c, 20, 3.0)  # 3 s holds one bar (1.9 s) of build
    r = out["args"]["input"]["requiredRegionsAtOffsets"][0]
    drop_ms = round(next(d for d in c["drops"] if d["main"])["time"] * 1000)
    assert r["offsetMsInEdit"] + drop_ms - r["startMs"] == 3000 and r["offsetMsInEdit"] >= 0
    with pytest.raises(cut.CutError):
        cut.edit_input(c, 10, 10.5)
    with pytest.raises(cut.CutError):
        cut.edit_input(c, 400, 10)
    with pytest.raises(cut.CutError):
        cut.edit_input(c, 30, 29.5)  # under one bar after the hit


def test_cut_without_stems_uses_the_first_peak_after_bar_1():
    c = tc(stems=False)
    d = cut.pick_drop(c)
    assert d["bar"] == 9 and "no drops" in d["source"]
    assert cut.pick_drop(tc(), "bar:10")["bar"] == 10


# ---------------------------------------------------------------- the second ear

def suno_like(c, bpm=None, key="G minor", shift_bars=0, extra_bar=None, phase_beats=0.0):
    """A Suno-shaped analysis of the template card: downbeats on its grid, sections at its boundaries."""
    b, b1 = grid.project_bpm(c), grid.bar1(c)
    bl = grid.bar_len(b)
    first = b1 + phase_beats * bl / 4
    beats = []
    n = int((c["duration"] - first) / (bl / 4))
    for i in range(n):
        beats.append({"time": round(first + i * bl / 4, 3), "bar_position": i % 4 + 1})
    starts = [s["start_bar"] for s in c["sections"]]
    starts = [starts[0]] + [s + (shift_bars if i == 2 else 0) for i, s in enumerate(starts[1:], 1)]
    if extra_bar:
        starts = sorted(starts + [extra_bar])
    times = [0.0] + [grid.time_of(s, b1, b) for s in starts[1:]] + [c["duration"]]
    secs = [{"label": f"S{i}", "duration_s": round(times[i + 1] - times[i], 3)} for i in range(len(times) - 1)]
    return {"status": "complete", "beats": {"bpm": bpm or b, "time_signature": "4/4", "key": key, "beats": beats},
            "sections": secs}


def test_second_ear_agrees_with_itself_and_reads_octave_tempo_as_agreement():
    c = tc()
    r = second_ear.compare(c, suno_like(c, bpm=63))
    assert r["tempo"]["agree"] and r["tempo"]["octave"]
    assert r["grid"]["agree"] and r["sections"]["agree"] and r["unread"] == []
    assert [q["what"] for q in r["questions"]] == ["key"]  # only: Suno settles trackcard's two-key doubt
    assert r["key"]["settles_alternative"] is False and "points to G minor" in r["questions"][0]["text"]


def test_second_ear_asks_about_a_two_bar_shift_a_new_section_a_wrong_tempo_and_the_grid():
    c = tc()
    c.pop("key_alternative_camelot")
    c["key_alternative"] = None
    r = second_ear.compare(c, suno_like(c, shift_bars=2, extra_bar=90))
    sec = [q for q in r["questions"] if q["what"] == "section"]
    assert {q["bar"] for q in sec} == {43, 41, 90}  # Suno's shifted start, trackcard's unmatched one, Suno's extra
    r = second_ear.compare(c, suno_like(c, bpm=124))
    assert not r["tempo"]["agree"] and any(q["what"] == "tempo" for q in r["questions"])
    r = second_ear.compare(c, suno_like(c, phase_beats=2))
    assert not r["grid"]["agree"] and r["grid"]["offset_beats"] == 2
    r = second_ear.compare(c, suno_like(c, key="A# major"))  # the relative major
    assert r["key"]["agree"] and r["key"]["relative"] and not any(q["what"] == "key" for q in r["questions"])
    r = second_ear.compare(c, suno_like(c, key="E major"))
    assert not r["key"]["agree"] and any(q["what"] == "key" for q in r["questions"])


def test_second_ear_says_what_it_could_not_read_and_keeps_no_suno_id():
    c = tc()
    r = second_ear.record(c, {"id": SUNO_CLIP, "status": "complete", "beats": {}, "sections": []}, "v1", "2026-11-24")
    assert set(r["unread"]) >= {"tempo", "key", "sections"}
    assert SUNO_CLIP not in json.dumps(r)


# ---------------------------------------------------------------- pro twins

def stem_card(full, enter_block, level=-12.0):
    s = copy.deepcopy(full)
    s["level_by_8_bars"] = [{**b, "rms_dbfs": (level if i >= enter_block else -70.0)} for i, b in enumerate(s["level_by_8_bars"])]
    return s


def test_twin_entries_and_lines_against_ours():
    full = tc()
    rec = twin.twin_record({"id": EPI_UUID, "title": "Zero One", "artists": "Young Community"}, full,
                           {"drums": stem_card(full, 0), "bass": stem_card(full, 2), "melody": stem_card(full, 1),
                            "instruments": stem_card(full, 3), "vocals": stem_card(full, 0, level=-90)})
    assert rec["entries"] == {"bass": 17, "drums": 1, "instruments": 25, "melody": 9, "vocals": None}
    assert rec["provenance"] == twin.PROVENANCE
    lines = twin.against(tc(), rec)
    assert "Bass: the twin brings it in at bar 17 (to the nearest 8); ours at bar 9." in lines
    assert any(l.startswith("Melody and instruments: the twin brings it in at bar 9") for l in lines)
    assert not any(l.startswith("Vocals") for l in lines)  # in neither track: no line
    assert twin.against(tc(stems=False), rec)[0].endswith("not measured (no stems).")


# ---------------------------------------------------------------- moves

RULES = [{"brain": "krish", "decided_by": "Krish", "approved_md": "taste/APPROVED.md",
          "claims": [{"id": "sound_design.growl_bass", "text": "Likes: growly"}]},
         {"brain": "calvin", "decided_by": "Calvin", "approved_md": "taste/calvin/APPROVED.md",
          "claims": [{"id": "vocal.vocal_chops", "text": "Likes: chopped vocals"}]}]


def brief_of(env):
    cfg, data, _ = env
    engine(cfg, data).run()
    return json.loads((cfg.clone / "engine/productions/sunrise/brief.json").read_text())


def test_moves_use_only_the_owners_rules_and_put_free_moves_first(env):
    b = brief_of(env)
    b["gaps"].append({**b["gaps"][0], "layer": "vocals", "bars": "57-64", "rule": "R9",
                      "splice": {"tool": "describe_a_sound", "args": {"query": "vocals vocal chops G minor", "type": "loop",
                                                                      "bpm_min": 124, "bpm_max": 128}}})
    k = moves.plan_moves(b, RULES, owner="krish")
    c = moves.plan_moves(b, RULES, owner="calvin")
    kq = [m["args"]["query"] for m in k if m["kind"] == "splice_search"]
    cq = [m["args"]["query"] for m in c if m["kind"] == "splice_search"]
    assert any(q.startswith("growly ") for q in kq) and not any("chopped" in q for q in kq)
    assert any(q.startswith("chopped ") for q in cq) and not any("growly" in q for q in cq)
    gates = [m["gate"] for m in k]
    assert gates == sorted(gates, key=["free", "standing_yes", "yes_each"].index)
    assert next(m for m in k if m["kind"] == "suno_second_ear")["gate"] == "standing_yes"
    assert all(m["gate"] == "yes_each" for m in k if m["kind"] in ("suno_sound", "suno_sketch_midi"))
    char = next(m for m in k if m.get("rules") == ["sound_design.growl_bass"])
    assert "post_filter" in char and "g minor" in char["post_filter"]["keys"]
    assert len({m["id"] for m in k}) == len(k)  # ids are unique and stable
    assert [m["id"] for m in moves.plan_moves(b, RULES, owner="krish")] == [m["id"] for m in k]


def test_moves_default_owner_is_the_latest_uploader_and_proposals_never_count(env):
    b = brief_of(env)
    owner = next(v["by"] for v in b["versions"] if v["id"] == b["latest_version"])
    ms = moves.plan_moves(b, RULES)
    assert all(m["owner_brain"] == owner for m in ms)
    proposed = [{"brain": owner, "claims": []}]  # the engine passes accepted claims only
    assert not any(m.get("rules") for m in moves.plan_moves(b, proposed))


def test_move_args_fit_the_live_tool_schemas(env):
    """Field sets of the connectors as read on 2026-11-24 (Splice describe_a_sound, Suno sounds-create, audio-create,
    audio-upload-create, audio-analysis, audio-midi; Epidemic SearchRecordings)."""
    b = brief_of(env)
    b["context"]["key"]["alternative"] = None  # a confirmed key: pitched layers carry it
    for g in b["gaps"]:
        g["splice"].pop("key_confirm_needed", None)
    ms = moves.plan_moves(b, RULES, owner="krish")
    suno_keys = {f"{p}{m}" for p in ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B") for m in ("", "m")}
    for m in ms:
        if m["kind"] == "splice_search":
            assert set(m["args"]) <= {"query", "bpm_min", "bpm_max", "type"} and m["args"]["type"] == "loop"
            assert not any(g in m["args"]["query"] for g in ("house", "techno", "melodic"))  # no genre words
        if m["kind"] == "suno_sound":
            assert set(m["args"]) <= {"description", "idempotency_key", "key", "loop", "tempo", "title"}
            assert m["args"].get("key") in suno_keys and 1 <= m["args"]["tempo"] <= 300
        if m["kind"] == "suno_sketch_midi":
            a = m["steps"][0]["args"]
            assert m["steps"][0]["tool"] == "audio-create" and a["instrumental"] is True
            assert 15 <= a["duration"] <= 360 and "description" not in a and "lyrics" not in a
            assert m["steps"][1]["tool"] == "audio-midi" and m["steps"][1]["cost"]["credits"] == 10
        if m["kind"] == "epidemic_twin":
            q = m["steps"][0]["args"]["query"]["externalID"]
            assert q["type"] == "SPOTIFY_TRACK" and len(q["id"]) == 22
        if m["kind"] == "suno_second_ear":
            assert [s["tool"] for s in m["steps"]] == ["audio-upload-create", "audio-upload-complete", "audio-analysis"]


def test_second_ear_reads_key_spellings():
    for t, code in (("G minor", "6A"), ("G Minor", "6A"), ("Gm", "6A"), ("gmin", "6A"), ("A# major", "6B"),
                    ("Bb major", "6B"), ("B♭", "6B"), ("7A", "7A"), ("F#m", "11A")):
        assert second_ear.camelot_of(t) == code, t
    assert second_ear.camelot_of("weird") is None


def test_key_helpers():
    assert moves.suno_key("G minor") == "Gm" and moves.suno_key("D# major") == "D#" and moves.suno_key(None) is None
    assert moves.key_ok("g", "6A") and moves.key_ok("g minor", "6A") and moves.key_ok("d minor", "6A")
    assert moves.key_ok("a# major", "6A") and not moves.key_ok("a minor", "6A") and moves.key_ok(None, "6A")
    assert moves.key_ok("bb", "6A")  # B-flat spelled with a flat: the relative major's note


# ---------------------------------------------------------------- ledger and the North Star

def row(**kw):
    r = {"move": "m-1", "kind": "splice_search", "version": "v1", "who": "krish", "on": "2026-11-24",
         "pick": {"provider": "splice", "id": SPLICE_UUID}, "gap": {"rule": "R8", "layer": "pads", "bars": "90-98"}}
    r.update(kw)
    return r


def test_ledger_keeps_catalog_ids_hashes_suno_and_refuses_private_things(tmp_path):
    p = tmp_path / "moves.jsonl"
    assert ledger.append(p, row()) and not ledger.append(p, row())  # the same pick twice is one row
    with pytest.raises(ledger.LedgerError):
        ledger.validate(row(pick={"provider": "suno", "id": SUNO_CLIP}))
    h = ledger.private_hash(SUNO_CLIP)
    assert ledger.validate(row(pick={"provider": "suno", "hash": h}))
    with pytest.raises(ledger.LedgerError):
        ledger.validate(row(pick={"provider": "splice", "id": "not-a-uuid"}))
    with pytest.raises(ledger.LedgerError, match="privacy"):
        ledger.validate(row(note="heard at https://suno.com/song/" + SUNO_CLIP))
    with pytest.raises(ledger.LedgerError):
        ledger.validate(row(who="someone"))
    assert SUNO_CLIP not in p.read_text()


def test_a_pick_on_the_earlier_version_is_credited_when_the_next_bounce_closes_the_gap(env):
    cfg, data, tmp = env
    k1, k2 = key_of(fake_id(1)), key_of(fake_id(2))  # k2 (11.5) is older than k1 (11.13)
    ledger.append(ledger.path_for(cfg.clone, "sunrise"), row(version=k2))
    engine(cfg, data, FakeMeasurer({k2: card(k2, extra_gap=True), k1: card(k1)})).run()
    b = json.loads((cfg.clone / "engine/productions/sunrise/brief.json").read_text())
    closed = b["changes"]["gaps"]["closed"]
    assert len(closed) == 1 and closed[0]["layer"] == "pads"
    assert closed[0]["closed_by"] == [{"move": "m-1", "provider": "splice", "who": "krish", "on": "2026-11-24"}]
    assert "after a Studio pick: splice pick by Krish" in (cfg.clone / "engine/productions/sunrise/BRIEF.md").read_text()
    status = (cfg.clone / "engine/STATUS.md").read_text()
    assert "## North Star: gaps closed per bounce" in status and "1 after a Studio pick" in status
    reg = json.loads((cfg.clone / "engine/productions/registry.json").read_text())
    sc = ledger.score(reg, cfg.clone / "engine/productions/cards", cfg.clone)
    assert sc["gaps_closed"] == 1 and sc["studio_closed"] == 1 and sc["bounces"] == 2 and sc["per_bounce"] == 0.5


def test_a_pick_made_on_the_closing_version_itself_is_not_credited():
    closed = [{"rule": "R8", "layer": "pads", "bars": "90-98", "gap": "bare"}]
    assert ledger.credit(closed, [row(version="v2")], {"v1"})[0]["closed_by"] == []
    assert ledger.credit(closed, [row(version="v1", gap={"layer": "bass", "bars": "90-98"})], {"v1"})[0]["closed_by"] == []
    assert ledger.credit(closed, [row(version="v1", gap={"layer": "pads", "bars": "1-8"})], {"v1"})[0]["closed_by"] == []
    assert ledger.credit(closed, [row(version="v1", pick={"provider": "none"})], {"v1"})[0]["closed_by"] == []


# ---------------------------------------------------------------- the brief v2 and STATUS

def test_brief_v2_carries_studio_files_and_stays_private(env):
    cfg, data, tmp = env
    engine(cfg, data).run()
    d = cfg.clone / "engine/productions/sunrise"
    b = json.loads((d / "brief.json").read_text())
    vid = b["latest_version"]
    ear = second_ear.record(card(vid), suno_like(card(vid), extra_bar=90), vid, "2026-11-24")
    (d / "ear").mkdir()
    (d / "ear" / f"{vid}.json").write_text(json.dumps(ear))
    (d / "twins").mkdir()
    full = card(vid)
    (d / "twins" / f"{EPI_UUID}.json").write_text(json.dumps(twin.twin_record(
        {"id": EPI_UUID, "title": "Zero One", "artists": "Young Community"}, full, {"bass": stem_card(full, 2)})))
    engine(cfg, data).run()
    b = json.loads((d / "brief.json").read_text())
    assert b["second_ear"]["version"] == vid and b["twins"][0]["recording_id"] == EPI_UUID
    assert {t["brain"] for t in b["targets"]} == {"krish", "calvin"}
    md = (d / "BRIEF.md").read_text()
    for h in ("## Second ear (Suno)", "## Against the target", "## Pro twins (Epidemic Sound)", "## Studio moves"):
        assert h in md
    status = (cfg.clone / "engine/STATUS.md").read_text()
    assert "Ear-check, [Sunrise]" in status and "Bar 90" in status
    text = all_text(cfg.clone / "engine")
    assert not privacy.scan(text) and SUNO_CLIP not in text


def test_targets_compare_the_bounce_with_each_brains_playlist(tmp_path):
    clone = make_clone(tmp_path)
    t = targets.brain_targets(clone)
    assert t["krish"]["bpm"]["median"] == 122 and t["krish"]["tracks"] >= 300
    lines = {x["brain"]: x["lines"] for x in targets.against(tc(), clone, t)}
    intro = next(l for l in lines["krish"] if l["what"] == "intro_bars_before_first_peak")
    assert intro["ours"] == 0  # full energy from the first bar
    tempo = next(l for l in lines["krish"] if l["what"] == "bpm")
    assert tempo["ours"] == 126 and tempo["where"] == "above the middle half"


# ---------------------------------------------------------------- revealed taste

def test_revealed_keeps_links_titles_artists_and_a_band_only(tmp_path):
    ok = [{"link": "https://open.spotify.com/track/1aNewTrackAAAAAAAAAAAA", "title": "New Song", "artists": "A",
           "rank_band": "top50"}]
    p = revealed.write(tmp_path, "krish", ok + ok)
    assert p.read_text().splitlines() == ["id,title,artists,link,rank_band",
                                          "1aNewTrackAAAAAAAAAAAA,New Song,A,https://open.spotify.com/track/1aNewTrackAAAAAAAAAAAA,top50"]
    for bad in ({**ok[0], "play_count": 41}, {**ok[0], "rank_band": "3"}, {**ok[0], "link": "spotify:track:x"},
                {**ok[0], "played_at": "2026-11-20"}):
        with pytest.raises(revealed.RevealedError):
            revealed.clean([bad])


def test_revealed_tracks_feed_only_their_owners_brain(tmp_path, monkeypatch):
    import shutil
    import test_engine_words as tw
    from trackcard.engine import measure as ms
    clone = make_clone(tmp_path)
    shutil.copytree(REPO / "engine", clone / "engine", ignore=shutil.ignore_patterns("productions", "references"))
    cfg = make_cfg(tmp_path, clone, max_per_run=10)
    metas = {tw.T_NEW: ("New Song", "Artist A", 240), tw.T_OLD: ("On The Ground", "oskar med k", 300)}
    monkeypatch.setattr(ms, "spotify_meta", lambda tid: dict(zip(("title", "artists", "duration_s"), metas[tid])))
    monkeypatch.setattr(ms, "soundcloud_match", lambda cfg, a, t, s: f"https://soundcloud.com/x/{t.replace(' ', '-')}")

    def fetch(cfg, url, stem):
        stem.parent.mkdir(parents=True, exist_ok=True)
        stem.with_suffix(".wav").write_bytes(b"RIFF")
        return stem.with_suffix(".wav")

    def analyze(cfg, wav, out, bpm=None, key=None):
        c = card(wav.stem, duration=float(metas[wav.stem][2]))
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{wav.stem}.trackcard.json").write_text(json.dumps(c))
        (out / f"{wav.stem}.trackcard.md").write_text("# card\n")
        return c, ""

    monkeypatch.setattr(ms, "fetch_audio", fetch)
    monkeypatch.setattr(ms, "analyze", analyze)
    revealed.write(clone, "krish", [{"link": f"https://open.spotify.com/track/{tw.T_NEW}", "title": "New Song",
                                     "artists": "Artist A", "rank_band": "top50"}])
    tw.run(cfg, rows=None)
    feed = (clone / "engine/references/krish/tracks.csv").read_text()
    assert tw.T_NEW in feed and "revealed: on the person's Spotify most-played list" in feed
    calvin = clone / "engine/references/calvin/tracks.csv"
    assert not calvin.exists() or tw.T_NEW not in calvin.read_text()
    idx = (clone / "engine/references/index.csv").read_text()
    assert "spotify_top" in idx


# ---------------------------------------------------------------- the CLI

def test_cli_cut_record_ear_and_score(env, tmp_path):
    cfg, data, _ = env
    engine(cfg, data).run()
    clone = str(cfg.clone)
    r = CliRunner()
    cf = tmp_path / "epi.trackcard.json"
    cf.write_text(json.dumps(tc()))
    out = r.invoke(main, ["studio", "cut", "--card", str(cf), "--length", "30", "--hit", "12.4",
                          "--recording-id", EPI_UUID])
    assert out.exit_code == 0, out.output
    assert json.loads(out.stdout)["input"]["requiredRegionsAtOffsets"]
    b = json.loads((cfg.clone / "engine/productions/sunrise/brief.json").read_text())
    sp = next(m for m in b["moves"] if m["kind"] == "splice_search")
    out = r.invoke(main, ["studio", "record", "sunrise", "--clone", clone, "--move", sp["id"], "--who", "krish",
                          "--pick", f"splice:{SPLICE_UUID}", "--on", "2026-11-24"])
    assert out.exit_code == 0 and "recorded" in out.output, out.output
    sk = next(m for m in b["moves"] if m["kind"] == "suno_sketch_midi")
    out = r.invoke(main, ["studio", "record", "sunrise", "--clone", clone, "--move", sk["id"], "--who", "calvin",
                          "--suno-clip", SUNO_CLIP, "--credits", "20", "--on", "2026-11-24"])
    assert out.exit_code == 0, out.output
    led = (cfg.clone / "engine/productions/sunrise/moves.jsonl").read_text()
    assert SUNO_CLIP not in led and ledger.private_hash(SUNO_CLIP) in led
    an = tmp_path / "analysis.json"
    an.write_text(json.dumps({**suno_like(card(b["latest_version"])), "id": SUNO_CLIP}))
    out = r.invoke(main, ["studio", "ear", "sunrise", "--clone", clone, "--analysis", str(an), "--on", "2026-11-24"])
    assert out.exit_code == 0, out.output
    ear = (cfg.clone / "engine/productions/sunrise/ear" / f"{b['latest_version']}.json").read_text()
    assert SUNO_CLIP not in ear
    out = r.invoke(main, ["studio", "score", "--clone", clone])
    assert out.exit_code == 0 and "gaps closed per bounce" in out.output
    out = r.invoke(main, ["studio", "moves", "sunrise", "--clone", clone, "--owner", "krish"])
    assert out.exit_code == 0 and "suno_second_ear" in out.output


def test_privacy_gate_refuses_suno_links_and_signed_urls():
    assert "suno_link" in privacy.scan(f"https://suno.com/song/{SUNO_CLIP}")
    assert "suno_link" in privacy.scan("https://cdn1.suno.ai/abc.mp3")
    assert "signed_url" in privacy.scan("https://x.s3.amazonaws.com/a.wav?X-Amz-Signature=abc")
    assert privacy.scan(f"https://splice.com/sounds/sample/abc/x-wav and {EPI_UUID}") == []


# ---------------------------------------------------------------- regressions from the review of 2026-11-24

def test_two_rules_on_the_same_layer_and_bars_get_distinct_moves_and_credit(env):
    b = brief_of(env)
    g = {**b["gaps"][0], "layer": "pads", "bars": "1-16", "rule": "R6",
         "splice": {"tool": "describe_a_sound", "args": {"query": "pads pads", "type": "loop", "bpm_min": 124, "bpm_max": 128}}}
    b["gaps"] = [g, {**g, "rule": "R8"}]
    ms = moves.plan_moves(b, RULES, owner="krish")
    assert len({m["id"] for m in ms}) == len(ms)
    r8 = next(m for m in ms if m["kind"] == "splice_search" and m["gap"]["rule"] == "R8")
    closed = [{"rule": "R8", "layer": "pads", "bars": "1-16", "gap": "bare"}]
    assert ledger.credit(closed, [row(move=r8["id"], version="v1", gap=r8["gap"])], {"v1"})[0]["closed_by"]


def test_an_unsure_key_never_reaches_a_paid_call_and_widens_the_filter(env):
    b = brief_of(env)  # the template card: G minor, maybe D# major
    ms = moves.plan_moves(b, RULES, owner="krish")
    sound = next(m for m in ms if m["kind"] == "suno_sound")
    assert "key" not in sound["args"] and sound["key_confirm_needed"]
    sketch = next(m for m in ms if m["kind"] == "suno_sketch_midi")
    assert "G minor" not in sketch["steps"][0]["args"]["style"] and sketch["key_confirm_needed"]
    char = next(m for m in ms if m.get("rules"))
    assert "d# major" in char["post_filter"]["keys"] and "g minor" in char["post_filter"]["keys"]


def test_second_ear_lead_in_string_tempo_and_cut_drop_parsing():
    c = tc()
    shift = 1.0
    c["level_by_8_bars"] = [{**x, "start": x["start"] + shift} for x in c["level_by_8_bars"]]
    for s in c["sections"]:
        s["start"] += shift
    a = suno_like(c)
    a["sections"][0]["start_s"] = grid.bar1(c)  # Suno's intro starts on the first downbeat
    r = second_ear.compare(c, a)
    assert 1 not in r["sections"]["only_suno"]
    r = second_ear.compare(tc(), {**suno_like(tc()), "beats": {**suno_like(tc())["beats"], "bpm": "124.0"}})
    assert r["tempo"]["suno"] == 124.0 and not r["tempo"]["agree"]
    assert "tempo" in second_ear.read_analysis({"beats": {"bpm": "fast"}})["unread"]
    for bad in ("bar:x", "bar58", "first"):
        with pytest.raises(cut.CutError):
            cut.pick_drop(tc(), bad)


def test_broken_studio_files_never_stop_the_engine(env):
    cfg, data, _ = env
    d = cfg.clone / "engine/productions/sunrise"
    d.mkdir(parents=True)
    (d / "moves.jsonl").write_text('{"move": "m-1"\n' + json.dumps(row()) + "\n")
    (d / "twins").mkdir()
    (d / "twins" / "x.json").write_text('{"title": "no entries"}')
    engine(cfg, data).run()
    assert (d / "brief.json").exists() and ledger.bad_lines(d / "moves.jsonl") == 1 and len(ledger.read(d / "moves.jsonl")) == 1


def test_twin_lines_read_plainly_when_the_twin_lacks_a_layer():
    full = tc()
    lines = twin.against(tc(), twin.twin_record({"id": EPI_UUID}, full, {"bass": stem_card(full, 2)}))
    assert "Drums: the twin has none; ours at bar 1." in lines
