"""The production engine end to end on synthetic listings: classification, measuring, briefs, idempotency, retries,
the privacy gate and the rolling PR (against a local bare repository and a fake gh)."""
import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

from engine_helpers import (CALVIN, INSP_FOLDER, KRISH, PROD_FOLDER, STRANGER, FakeMeasurer, all_text, card, entry,
                            fake_id, files_for, git, make_clone, make_cfg)
from trackcard.engine import privacy
from trackcard.engine.run import Engine, classify, resume
from trackcard.engine.sources import FixtureSource, key_of

ZIP = "WhatsApp Chat with +44 7700 900123.zip"


def listing():
    return {"productions": [
        entry(1, "Sunrise 11.13 .wav", btime="2026-11-13T20:39:35Z"),
        entry(2, "Sunrise 11.5 edits.wav", btime="2026-11-05T17:42:28Z", owner=KRISH),
        entry(3, "Archive", isdir=True, mime="inode/directory"),
        entry(4, "Sunrise (1).wav", path="Archive/Sunrise (1).wav", btime="2026-10-22T13:11:29Z", owner=KRISH),
        entry(5, "late night beat v3.wav", path="Archive/late night beat v3.wav", btime="2026-10-22T13:11:29Z", owner=KRISH),
        entry(6, ZIP, path=f"Archive/{ZIP}", mime="application/zip", owner=STRANGER),
        entry(7, "Stems", isdir=True, mime="inode/directory"),
        entry(8, "kick.wav", path="Stems/kick.wav"),
        {**entry(9, "Inspiration", isdir=True, mime="inode/directory"), "ID": INSP_FOLDER},
        entry(10, "x.txt", path="Inspiration/x.txt", mime="text/plain"),
    ], "inspiration": []}


@pytest.fixture
def env(tmp_path):
    clone = make_clone(tmp_path)
    cfg = make_cfg(tmp_path, clone)
    data = listing()
    data["files"] = files_for(data, tmp_path)
    return cfg, data, tmp_path


def engine(cfg, data, measurer=None, **kw):
    return Engine(cfg, FixtureSource(cfg, data), measurer=measurer or FakeMeasurer(), **kw)


def test_classifies_versions_archive_and_skips_the_rest(env):
    cfg, data, _ = env
    src = FixtureSource(cfg, data)
    lst = src.list()
    assert lst.ignored == 1 and lst.other_folders == 1  # the zip, and Stems/kick.wav
    reg = classify(lst, {}, {}).registry
    assert set(reg["projects"]) == {"sunrise", "late-night-beat"}
    vs = reg["projects"]["sunrise"]["versions"]
    order = [v["source_name"] for _, v in sorted(vs.items(), key=lambda kv: kv[1]["date"])]
    assert order == ["Sunrise (1).wav", "Sunrise 11.5 edits.wav", "Sunrise 11.13 .wav"]
    by = {v["source_name"]: v["by"] for v in vs.values()}
    assert by == {"Sunrise (1).wav": "krish", "Sunrise 11.5 edits.wav": "krish", "Sunrise 11.13 .wav": "calvin"}


def test_run_writes_cards_briefs_status_and_nothing_private(env):
    cfg, data, tmp = env
    cfg = make_cfg(tmp, cfg.clone, max_per_run=10)
    res = engine(cfg, data).run()
    root = cfg.clone / "engine"
    reg = json.loads((root / "productions/registry.json").read_text())
    assert all(v["status"] == "measured" for p in reg["projects"].values() for v in p["versions"].values())
    brief = json.loads((root / "productions/sunrise/brief.json").read_text())
    assert brief["latest_version"] == key_of(fake_id(1)) and brief["changes"]["from"] == key_of(fake_id(2))
    assert brief["project"]["archived"] is False
    assert json.loads((root / "productions/late-night-beat/brief.json").read_text())["project"]["archived"] is True
    md = (root / "productions/sunrise/BRIEF.md").read_text()
    assert "## What changed since the previous version" in md and "Krish's brain" in md
    status = (root / "STATUS.md").read_text()
    assert "1 file(s) of a kind" in status and "1 file(s) in Music Production subfolders" in status
    text = all_text(cfg.clone / "engine")
    for sentinel in [fake_id(n) for n in range(1, 11)] + [KRISH, CALVIN, STRANGER, PROD_FOLDER, INSP_FOLDER,
                                                        "private note sentinel", "WhatsApp", "7700"]:
        assert sentinel not in text
    assert len(res.measured) == 4


def test_second_run_and_a_shuffled_listing_change_no_byte(env):
    cfg, data, tmp = env
    cfg = make_cfg(tmp, cfg.clone, max_per_run=10)
    engine(cfg, data).run()
    before = {p: p.read_bytes() for p in (cfg.clone / "engine").rglob("*") if p.is_file()}
    data2 = {**data, "productions": random.Random(4).sample(data["productions"], len(data["productions"]))}
    m = FakeMeasurer()
    engine(cfg, data2, m).run()
    after = {p: p.read_bytes() for p in (cfg.clone / "engine").rglob("*") if p.is_file()}
    assert before == after and m.calls == []


def test_cap_one_over_runs_equals_one_big_run(env, tmp_path):
    cfg, data, tmp = env
    for _ in range(5):
        engine(make_cfg(tmp, cfg.clone, max_per_run=1), data).run()
    small = (cfg.clone / "engine/productions/registry.json").read_text()
    clone2 = make_clone(tmp_path / "b")
    engine(make_cfg(tmp_path / "b", clone2, max_per_run=10), data).run()
    assert small == (clone2 / "engine/productions/registry.json").read_text()


def test_newest_first_and_failures_give_up_after_three_tries(env):
    cfg, data, _ = env
    bad = key_of(fake_id(1))
    m = FakeMeasurer(fail={bad})
    for _ in range(3):
        engine(cfg, data, m).run()
    assert m.calls[0] == bad  # the newest bounce goes first
    reg = json.loads((cfg.clone / "engine/productions/registry.json").read_text())
    v = reg["projects"]["sunrise"]["versions"][bad]
    assert v["status"] == "gave_up" and v["why"] == "trackcard_failed_no_stems"
    n = m.calls.count(bad)
    engine(cfg, data, m).run()
    assert m.calls.count(bad) == n == 3
    assert "Gave up after 3 tries" in (cfg.clone / "engine/STATUS.md").read_text()


def test_a_crash_mid_measure_still_counts_as_a_try(env):
    cfg, data, _ = env

    def boom(*a, **k):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        engine(cfg, data, boom).run()
    from trackcard.engine.run import State
    assert State(cfg.state_file).tries(key_of(fake_id(1))) == 1
    assert not any(cfg.work_dir.iterdir())


def test_stems_versus_no_stems_is_not_comparable(env):
    cfg, data, tmp = env
    cfg = make_cfg(tmp, cfg.clone, max_per_run=10)
    k1, k2 = key_of(fake_id(1)), key_of(fake_id(2))
    engine(cfg, data, FakeMeasurer({k1: card(k1, stems=False), k2: card(k2)})).run()
    b = json.loads((cfg.clone / "engine/productions/sunrise/brief.json").read_text())
    assert b["changes"]["comparable_stems"] is False and "gaps" not in b["changes"]
    assert b["context"]["drops"] is None and b["gaps_partial"]
    assert "not comparable" in (cfg.clone / "engine/productions/sunrise/BRIEF.md").read_text()


def test_gap_changes_pair_by_rule_layer_and_bars(env):
    cfg, data, tmp = env
    cfg = make_cfg(tmp, cfg.clone, max_per_run=10)
    k1, k2 = key_of(fake_id(1)), key_of(fake_id(2))
    engine(cfg, data, FakeMeasurer({k1: card(k1, extra_gap=True, drop_bar=60), k2: card(k2)})).run()
    ch = json.loads((cfg.clone / "engine/productions/sunrise/brief.json").read_text())["changes"]
    assert ch["gaps"]["opened"] == [{"rule": "R8", "layer": "pads", "bars": "90-98", "gap": "low-energy section is very bare"}]
    assert ch["gaps"]["closed"] == [] and ch["gaps"]["still_open"] == len(card(k2)["brief"])


def test_splice_args_match_the_live_tool(env):
    cfg, data, tmp = env
    engine(make_cfg(tmp, cfg.clone, max_per_run=10), data).run()
    b = json.loads((cfg.clone / "engine/productions/sunrise/brief.json").read_text())
    describe_a_sound = {"query", "bpm_min", "bpm_max", "type"}  # mcp__Splice__describe_a_sound, read 2026-11-16
    for g in b["gaps"]:
        assert g["splice"]["tool"] == "describe_a_sound" and set(g["splice"]["args"]) <= describe_a_sound
        assert isinstance(g["splice"]["args"]["bpm_min"], int) and g["splice"]["args"]["type"] == "loop"
    v1 = {"schema_version", "project", "as_of", "latest_version", "source_card", "trackcard_version", "context",
          "gaps", "gaps_partial", "changes", "rules", "references", "versions"}
    assert v1 | {"moves", "targets", "second_ear", "twins"} == set(b) and b["schema_version"] == 2  # v2 only adds keys
    assert b["context"]["bar1_s"] is not None and b["context"]["tempo"]["bpm"]


def test_reupload_is_a_copy_and_content_change_is_a_new_version(env):
    cfg, data, tmp = env
    cfg = make_cfg(tmp, cfg.clone, max_per_run=10)
    engine(cfg, data).run()
    md5 = data["productions"][0]["Hashes"]["md5"]
    data["productions"].append(entry(20, "Sunrise 11.13 (1).wav", md5=md5, btime="2026-11-14T10:00:00Z"))
    data["productions"][1]["Hashes"]["md5"] = "f" * 32  # the 11.5 file replaced in place
    data["files"] = files_for(data, tmp)
    m = FakeMeasurer()
    engine(cfg, data, m).run()
    vs = json.loads((cfg.clone / "engine/productions/registry.json").read_text())["projects"]["sunrise"]["versions"]
    k20, k2 = key_of(fake_id(20)), key_of(fake_id(2))
    assert vs[k20]["status"] == "copy_of" and vs[k20]["copy_of"] == key_of(fake_id(1))
    assert vs[k2]["present"] is False and vs[f"{k2}-r2"]["status"] == "measured" and m.calls == [f"{k2}-r2"]


def test_lossless_is_measured_and_the_mp3_twin_is_an_alternate(env):
    cfg, data, tmp = env
    data["productions"] += [entry(30, "Moonset 11.20.mp3", btime="2026-11-20T10:00:00Z"),
                            entry(31, "Moonset 11.20.wav", btime="2026-11-20T10:05:00Z")]
    data["files"] = files_for(data, tmp)
    reg = classify(FixtureSource(cfg, data).list(), {}, {}).registry
    vs = reg["projects"]["moonset"]["versions"]
    assert vs[key_of(fake_id(30))]["status"] == "alternate" and vs[key_of(fake_id(31))]["status"] == "queued"


def test_questions_and_aliases(env):
    cfg, data, tmp = env
    cfg = make_cfg(tmp, cfg.clone, max_per_run=10)
    data["productions"].append(entry(40, "Sunrize 11.20.wav", btime="2026-11-20T10:00:00Z"))
    data["files"] = files_for(data, tmp)
    engine(cfg, data).run()
    k = key_of(fake_id(40))
    status = (cfg.clone / "engine/STATUS.md").read_text()
    assert "Sunrize 11.20.wav" in status and f'"{k}": {{"project": "<slug>"}}' in status
    (cfg.clone / "engine/productions/aliases.json").write_text(json.dumps({k: {"project": "sunrise", "date": "2026-11-21"}}))
    engine(cfg, data).run()
    vs = json.loads((cfg.clone / "engine/productions/registry.json").read_text())["projects"]["sunrise"]["versions"]
    assert vs[k]["date"] == "2026-11-21" and vs[k]["date_source"] == "alias"
    card_path = cfg.clone / f"engine/productions/cards/{k}.trackcard.json"
    before = card_path.read_bytes()
    (cfg.clone / "engine/productions/aliases.json").write_text(json.dumps({k: {"project": "sunrise", "date": "2026-11-22"}}))
    engine(cfg, data).run()
    assert card_path.read_bytes() == before  # a date correction never moves or rewrites a card


def test_missing_owner_metadata_stops_the_run(env):
    cfg, data, _ = env
    del data["productions"][0]["Metadata"]["owner"]
    res = engine(cfg, data).run()
    assert res.code == 1 and not (cfg.clone / "engine").exists()


def test_privacy_scan_and_redact():
    rid = fake_id(1)
    assert privacy.scan(f"see https://drive.google.com/file/d/{rid}/view", set()) == ["google_link"]
    assert privacy.scan(f"x {rid} y", {rid}) == ["private_value"]
    assert privacy.scan("mail calvin.test@example.com", set()) == ["email"]
    assert privacy.scan("call +44 7700 900123", set()) == ["phone"]
    assert privacy.scan("https://soundcloud.com/a/b/s-AbC123", set()) == ["soundcloud_private"]
    assert privacy.scan("BPM 124-128, +4.1 dB, bars 17-24, -8.7 LUFS", set()) == []
    err = subprocess.TimeoutExpired(["rclone", "copyto", f"gdrive:{rid}", f"--drive-root-folder-id={PROD_FOLDER}"], 120)
    red = privacy.redact(repr(err), {rid, PROD_FOLDER})
    assert rid not in red and PROD_FOLDER not in red
    assert privacy.why(repr(err)) == "unexpected_error" and privacy.why("timeout") == "timeout"


# ---------------------------------------------------------------- publish against a real git remote and a fake gh

class FakeGh:
    def __init__(self, prs=None):
        self.prs, self.calls = prs or [], []

    def __call__(self, cmd, cwd, timeout=600):
        if cmd[0] != "gh":
            return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        self.calls.append(cmd)
        if cmd[1:3] == ["pr", "list"]:
            return subprocess.CompletedProcess(cmd, 0, json.dumps(self.prs), "")
        if cmd[1:3] == ["pr", "create"]:
            self.prs.append({"number": len(self.prs) + 1, "state": "OPEN", "mergedAt": None})
        return subprocess.CompletedProcess(cmd, 0, "", "")


@pytest.fixture
def remote(tmp_path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    seed = make_clone(tmp_path / "seed")
    git(seed, "init", "-q", "-b", "main")
    git(seed, "config", "user.email", "engine@users.noreply.github.com")
    git(seed, "config", "user.name", "engine")
    (seed / ".gitignore").write_text(
        (Path(__file__).resolve().parents[1] / ".gitignore").read_text())
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "seed")
    git(seed, "remote", "add", "origin", str(origin))
    git(seed, "push", "-q", "origin", "main")
    clone = tmp_path / "wc"
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
    git(clone, "config", "user.email", "engine@users.noreply.github.com")
    git(clone, "config", "user.name", "engine")
    return origin, clone


def test_publish_commits_pushes_and_opens_one_pr(env, remote):
    _, data, tmp = env
    origin, clone = remote
    cfg = make_cfg(tmp, clone, max_per_run=10)
    gh = FakeGh()
    res = Engine(cfg, FixtureSource(cfg, data), sh=gh, measurer=FakeMeasurer()).run(publish=True)
    assert res.code == 0
    files = git(clone, "ls-tree", "-r", "--name-only", "origin/engine/updates").split()
    assert "engine/productions/registry.json" in files and not any(f.endswith(".wav") for f in files)
    assert any(f.startswith("engine/productions/cards/") for f in files)
    creates = [c for c in gh.calls if c[1:3] == ["pr", "create"]]
    assert len(creates) == 1
    body = creates[0][creates[0].index("--body") + 1]
    msg = git(clone, "log", "-1", "--format=%B", "origin/engine/updates")
    for s in (fake_id(1), CALVIN, KRISH, PROD_FOLDER):
        assert s not in body and s not in msg
    # a second run with nothing new pushes nothing and edits nothing
    head = git(clone, "rev-parse", "origin/engine/updates")
    gh.calls.clear()
    Engine(cfg, FixtureSource(cfg, data), sh=gh, measurer=FakeMeasurer()).run(publish=True)
    assert git(clone, "rev-parse", "origin/engine/updates") == head
    assert not [c for c in gh.calls if c[1:3] in (["pr", "create"], ["pr", "edit"])]


def test_publish_after_merge_is_quiet(env, remote):
    _, data, tmp = env
    origin, clone = remote
    cfg = make_cfg(tmp, clone, max_per_run=10)
    gh = FakeGh()
    Engine(cfg, FixtureSource(cfg, data), sh=gh, measurer=FakeMeasurer()).run(publish=True)
    git(clone, "push", "-q", "origin", "origin/engine/updates:main")  # Krish merges
    gh.prs[-1].update(state="MERGED", mergedAt="2026-11-16T10:00:00Z")
    gh.calls.clear()
    Engine(cfg, FixtureSource(cfg, data), sh=gh, measurer=FakeMeasurer()).run(publish=True)
    assert not [c for c in gh.calls if c[1:3] == ["pr", "create"]]


def test_gate_blocks_a_planted_id(env, remote):
    _, data, tmp = env
    origin, clone = remote
    cfg = make_cfg(tmp, clone, max_per_run=10)
    data["productions"][0]["Name"] = data["productions"][0]["Path"] = f"Sunrise {fake_id(1)} 11.13.wav"
    gh = FakeGh()
    res = Engine(cfg, FixtureSource(cfg, data), sh=gh, measurer=FakeMeasurer()).run(publish=True)
    assert res.code == 3
    assert subprocess.run(["git", "rev-parse", "-q", "--verify", "origin/engine/updates"], cwd=clone,
                          capture_output=True).returncode != 0
    assert not [c for c in gh.calls if c[1:3] == ["pr", "create"]]
    assert fake_id(1) not in cfg.journal.read_text()


def test_closed_pr_pauses_until_resume(env, remote):
    _, data, tmp = env
    origin, clone = remote
    cfg = make_cfg(tmp, clone, max_per_run=10)
    gh = FakeGh([{"number": 7, "state": "CLOSED", "mergedAt": None}])
    Engine(cfg, FixtureSource(cfg, data), sh=gh, measurer=FakeMeasurer()).run(publish=True)
    assert json.loads(cfg.state_file.read_text())["paused"]["why"] == "pr_closed_unmerged"
    assert not [c for c in gh.calls if c[1:3] == ["pr", "create"]]
    assert "resumed" in resume(cfg)
    Engine(cfg, FixtureSource(cfg, data), sh=gh, measurer=FakeMeasurer()).run(publish=True)
    assert [c for c in gh.calls if c[1:3] == ["pr", "create"]]


def test_engine_cards_are_not_gitignored():
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run(["git", "check-ignore", "-q", "engine/productions/cards/abc.trackcard.json"], cwd=root)
    assert r.returncode == 1  # 1 = not ignored


def test_real_trackcard_through_the_production_path(env, tmp_path):
    """One real measurement (no stems) of a synthetic bounce, as the worker runs it."""
    import soundfile as sf
    sys.path.insert(0, str(Path(__file__).parent))
    from synth import SR, three_part_track
    cfg, data, tmp = env
    audio, _ = three_part_track()
    wav = tmp_path / "bounce.wav"
    sf.write(wav, audio, SR)
    data = {"productions": [entry(50, "Sunrise 11.13.wav")], "files": {fake_id(50): str(wav)}}
    from trackcard.engine import measure

    def no_stems(cfg, src, vid, out, bpm=None, key=None):
        return measure.measure_file(cfg, src, vid, out, bpm, key)

    cfg = make_cfg(tmp, cfg.clone, trackcard=f"{sys.executable} -m trackcard.cli")
    res = Engine(cfg, FixtureSource(cfg, data), measurer=no_stems).run()
    assert res.measured == [key_of(fake_id(50))]
    c = json.loads((cfg.clone / f"engine/productions/cards/{key_of(fake_id(50))}.trackcard.json").read_text())
    assert c["file"] == f"{key_of(fake_id(50))}.wav"
    assert (cfg.clone / "engine/productions/sunrise/BRIEF.md").exists()
    assert not any(cfg.work_dir.iterdir())
