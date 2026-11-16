"""Regressions for the defects found in the 2026-11-16 adversarial review of the engine."""
import json
import subprocess

from engine_helpers import CALVIN, KRISH, FakeMeasurer, card, entry, fake_id, files_for, git, make_cfg
from test_engine_run import FakeGh, env, listing, remote  # noqa: F401 (fixtures)
from trackcard.engine import names, privacy
from trackcard.engine.brief import latest
from trackcard.engine.run import Engine, classify
from trackcard.engine.sources import FixtureSource, key_of

NOV = "2026-11-21T10:00:00Z"


def test_readme_naming_and_dotted_versions():
    p = names.parse("Closure 11.20 drums.wav", NOV)
    assert (p.slug, p.date, p.note, p.ask) == ("closure", "2026-11-20", "drums", None)
    p = names.parse("Closure v2.1.wav", NOV)
    assert (p.slug, p.version, p.date_source) == ("closure", 2, "upload")


def test_contact_scan_for_free_text():
    assert privacy.scan_contacts("text me 415-555-0100") == ["phone"]
    assert privacy.scan_contacts("07700 900123") == ["phone"]
    assert privacy.scan_contacts("on.soundcloud.com/abc") == ["link"]
    assert privacy.scan_contacts("bars 17-24 at 124-128 BPM, 2026-11-20") == []
    assert privacy.scan("on.soundcloud.com/abc") == ["soundcloud_private"]


def test_latest_keeps_a_measured_version_alive_through_its_copy():
    vs = {"a": {"status": "measured", "present": False, "date": "2026-11-01", "folder": "production"},
          "b": {"status": "copy_of", "copy_of": "a", "present": True, "date": "2026-11-02", "folder": "production"}}
    assert latest(vs) == ("a", False)
    vs = {"a": {"status": "measured", "present": True, "date": "2026-11-01", "folder": "archive"},
          "b": {"status": "queued", "present": True, "date": "2026-11-02", "folder": "production"}}
    assert latest(vs) == ("a", False)  # a newer bounce waits outside Archive: not an archived project


def test_lossless_twin_after_the_lossy_one_was_measured(env):
    cfg, data, tmp = env
    data["productions"] = [entry(30, "Moonset 11.20.mp3", btime="2026-11-20T10:00:00Z")]
    data["files"] = files_for(data, tmp)
    old = classify(FixtureSource(cfg, data).list(), {}, {}).registry
    old["projects"]["moonset"]["versions"][key_of(fake_id(30))]["status"] = "measured"
    data["productions"].append(entry(31, "Moonset 11.20.wav", btime="2026-11-20T10:05:00Z"))
    vs = classify(FixtureSource(cfg, data).list(), old, {}).registry["projects"]["moonset"]["versions"]
    assert vs[key_of(fake_id(30))]["status"] == "alternate" and vs[key_of(fake_id(31))]["status"] == "queued"


def test_alias_title_wins_over_a_placeholder(env):
    cfg, data, tmp = env
    data["productions"] = [entry(40, "Untitled 11.20.wav", btime="2026-11-20T10:00:00Z")]
    k = key_of(fake_id(40))
    reg = classify(FixtureSource(cfg, data).list(), {}, {k: {"project": "Night Drive"}}).registry
    assert reg["projects"]["night-drive"]["title"] == "Night Drive"


def test_a_name_with_contact_details_is_withheld(env):
    cfg, data, tmp = env
    data["productions"] = [entry(41, "Sunrise call 415-555-0100.wav")]
    reg = classify(FixtureSource(cfg, data).list(), {}, {}).registry
    assert not reg["projects"] and list(reg["questions"].values())[0]["source_name"] == "(name withheld)"


def test_replaced_audio_before_merge_never_reuses_the_old_card(env):
    cfg, data, tmp = env
    cfg = make_cfg(tmp, cfg.clone, max_per_run=10)
    k = key_of(fake_id(1))
    m = FakeMeasurer({k: card(k, bpm=120)})
    Engine(cfg, FixtureSource(cfg, data), measurer=m).run()
    # simulate an unmerged branch: main never got the registry, but the cache holds the card
    (cfg.clone / "engine/productions/registry.json").unlink()
    for f in (cfg.clone / "engine/productions/cards").iterdir():
        f.unlink()
    data["productions"][0]["Hashes"]["md5"] = "e" * 32
    m2 = FakeMeasurer({k: card(k, bpm=128)})
    Engine(cfg, FixtureSource(cfg, data), measurer=m2).run()
    assert k in m2.calls  # measured again from the new audio
    c = json.loads((cfg.clone / f"engine/productions/cards/{k}.trackcard.json").read_text())
    assert c["likely_project_bpm"] == 128


def test_failed_pr_create_is_retried_and_forks_are_ignored(env, remote):
    _, data, tmp = env
    origin, clone = remote
    cfg = make_cfg(tmp, clone, max_per_run=10)

    class Flaky(FakeGh):
        fails = 1

        def __call__(self, cmd, cwd, timeout=600):
            if cmd[0] == "gh" and cmd[1:3] == ["pr", "create"] and self.fails:
                self.fails -= 1
                self.calls.append(cmd)
                return subprocess.CompletedProcess(cmd, 1, "", "")
            return super().__call__(cmd, cwd, timeout)

    gh = Flaky([{"number": 9, "state": "CLOSED", "mergedAt": None, "isCrossRepository": True}])
    assert Engine(cfg, FixtureSource(cfg, data), sh=gh, measurer=FakeMeasurer()).run(publish=True).code == 1
    assert Engine(cfg, FixtureSource(cfg, data), sh=gh, measurer=FakeMeasurer()).run(publish=True).code == 0
    assert [p for p in gh.prs if not p.get("isCrossRepository")]  # our PR exists; the fork's closed PR paused nothing
    assert not json.loads(cfg.state_file.read_text()).get("paused")


def test_deleted_head_branch_after_merge_does_not_block_pushes(env, remote):
    _, data, tmp = env
    origin, clone = remote
    cfg = make_cfg(tmp, clone, max_per_run=10)
    gh = FakeGh()
    Engine(cfg, FixtureSource(cfg, data), sh=gh, measurer=FakeMeasurer()).run(publish=True)
    git(clone, "push", "-q", "origin", "origin/engine/updates:main")
    git(clone, "push", "-q", "origin", "--delete", "engine/updates")  # GitHub's auto-delete after merge
    gh.prs[-1].update(state="MERGED", mergedAt="2026-11-16T10:00:00Z")
    data["productions"].append(entry(60, "Sunrise 11.20.wav", btime="2026-11-20T10:00:00Z", owner=CALVIN))
    data["files"] = files_for(data, tmp)
    res = Engine(cfg, FixtureSource(cfg, data), sh=gh, measurer=FakeMeasurer()).run(publish=True)
    assert res.code == 0 and len([c for c in gh.calls if c[1:3] == ["pr", "create"]]) == 2


def test_identity_from_environment_is_not_a_foreign_author(env, remote, monkeypatch):
    _, data, tmp = env
    origin, clone = remote
    git(clone, "config", "--unset", "user.email")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "engine@users.noreply.github.com")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "engine@users.noreply.github.com")
    cfg = make_cfg(tmp, clone, max_per_run=1)
    gh = FakeGh()
    Engine(cfg, FixtureSource(cfg, data), sh=gh, measurer=FakeMeasurer()).run(publish=True)
    Engine(cfg, FixtureSource(cfg, data), sh=gh, measurer=FakeMeasurer()).run(publish=True)
    assert not json.loads(cfg.state_file.read_text()).get("paused")
