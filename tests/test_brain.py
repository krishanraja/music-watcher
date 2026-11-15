"""Music Brain: evidence validation, recounting with withdrawal, weekly proposal budget, freezing, rejection memory."""
import datetime as dt
import json
import shutil
from pathlib import Path

import pytest

from trackcard import brain as br

REPO_TASTE = Path(__file__).resolve().parents[1] / "taste"
MONDAY = dt.date(2026, 11, 16)


@pytest.fixture
def taste(tmp_path):
    t = tmp_path / "taste"
    (t / "brain").mkdir(parents=True)
    (t / "graph").mkdir()
    for f in ("vocab.json", "policy.json"):
        shutil.copy(REPO_TASTE / "brain" / f, t / "brain" / f)
    ev = [
        {"id": "a", "who": "krish", "track": "T1", "where": "chat", "when": "2026-11-01", "text": "love the growly bass",
         "signals": [{"dim": "sound_design", "slug": "growl_bass", "polarity": 1, "strength": 3, "quote": "growly bass"}]},
        {"id": "b", "who": "calvin", "track": "T2", "where": "chat", "when": "2026-11-02", "text": "great vocal chops",
         "signals": [{"dim": "vocal", "slug": "vocal_chops", "polarity": 1, "strength": 2, "quote": "vocal chops"}]},
        {"id": "c", "who": "krish", "track": "T3", "where": "chat", "when": "2026-11-03", "text": "too many vocal chops",
         "signals": [{"dim": "vocal", "slug": "vocal_chops", "polarity": -1, "strength": 1, "quote": "too many vocal chops"}]},
    ]
    (t / "brain" / "evidence.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ev))
    head = "id,measured,full_track,bpm,mode,band_sub,band_low,band_mid,band_high-mid,band_air,crest_db,duration_s\n"
    rows = "".join(f"t{i},True,False,{122 if i < 8 else 100},minor,-3,0,-5,-13,-20,12,300\n" for i in range(12))
    (t / "graph" / "tracks.csv").write_text(head + rows)
    return t


def test_check_rejects_paraphrased_quotes_and_unknown_slugs(taste):
    b = br.load(taste)
    assert br.check(b) == []
    b.evidence[0]["signals"][0]["quote"] = "growling bass"
    b.evidence[1]["signals"][0]["slug"] = "chopz"
    probs = br.check(b)
    assert any("character for character" in p for p in probs)
    assert any("not in vocab.json" in p for p in probs)


def test_recount_counts_measured_and_words_and_both_ways(taste):
    pats = br.recount(br.load(taste))
    assert len(pats[("groove", "tempo_118_125")]["measured_tracks"]) == 8
    assert pats[("groove", "tempo_118_125")]["measured_share"] == pytest.approx(0.67, abs=0.01)
    assert pats[("vocal", "vocal_chops")]["both_ways"]
    assert pats[("sound_design", "growl_bass")]["eligible"] == 0  # words-only signal, not measurable


def test_withdrawn_evidence_stops_counting(taste):
    b = br.load(taste)
    b.evidence[0]["withdrawn"] = True
    assert ("sound_design", "growl_bass") not in br.recount(b)


def test_propose_respects_weekly_budget_and_freezes(taste):
    b = br.load(taste)
    first = br.propose(b, MONDAY)
    assert len(first) == 3
    assert br.propose(b, MONDAY + dt.timedelta(days=2)) == []  # same ISO week
    c = first[0]
    c["text"] = "edited after proposal"
    with pytest.raises(br.BrainError, match="frozen"):
        br.decide(b, c["id"], True)


def test_rejected_claim_is_never_proposed_again(taste):
    b = br.load(taste)
    c = br.propose(b, MONDAY)[0]
    br.decide(b, c["id"], False, "not me")
    br.save(b)
    b = br.load(taste)
    later = br.propose(b, MONDAY + dt.timedelta(weeks=1))
    assert c["id"] not in [x["id"] for x in later]


def test_accepted_claim_renders_and_flags_weakening(taste):
    b = br.load(taste)
    b.policy["proposals_per_week"] = 20
    claim = next(c for c in br.propose(b, MONDAY) if c["slug"] == "growl_bass")
    br.decide(b, claim["id"], True)
    approved, patterns = br.render(b)
    assert claim["text"] in approved and "weakened" not in approved
    b.evidence[0]["withdrawn"] = True
    approved, _ = br.render(b)
    assert "weakened" in approved


def test_repo_evidence_is_valid():
    b = br.load(REPO_TASTE)
    assert br.check(b) == []


def test_a_second_brain_counts_only_its_voices_and_names_its_decider(taste, tmp_path):
    """Calvin's brain: the shared vocabulary and evidence log, only Calvin's words, its own claims and decisions."""
    cal = taste / "calvin"
    (cal / "brain").mkdir(parents=True)
    (cal / "graph").mkdir()
    shutil.copy(taste / "graph" / "tracks.csv", cal / "graph" / "tracks.csv")
    policy = json.loads((taste / "brain" / "policy.json").read_text()) | {
        "voices": ["calvin"], "decides": "Calvin", "vocab": "../../brain/vocab.json", "evidence": "../../brain/evidence.jsonl"}
    (cal / "brain" / "policy.json").write_text(json.dumps(policy))
    b = br.load(cal)
    assert br.check(b) == [] and len(b.evidence) == 3  # every row is validated, whoever said it
    pats = br.recount(b)
    assert ("sound_design", "growl_bass") not in pats  # Krish's words do not count here
    assert pats[("vocal", "vocal_chops")]["words_like"] == 2 and not pats[("vocal", "vocal_chops")]["both_ways"]
    b.policy["proposals_per_week"] = 20
    claim = next(c for c in br.propose(b, MONDAY) if c["slug"] == "vocal_chops")
    approved, patterns = br.render(b)
    assert "## Waiting for Calvin" in approved and "taste/calvin/brain/claims.jsonl" in approved
    assert "`trackcard brain accept <id> --taste taste/calvin`" in approved
    assert "Calvin's words in `taste/brain/evidence.jsonl`" in " ".join(patterns.split())
    br.decide(b, claim["id"], True)
    br.save(b)
    assert (cal / "brain" / "claims.jsonl").exists() and not (taste / "brain" / "claims.jsonl").exists()
    approved, _ = br.render(b)
    assert "accepted by Calvin" in approved and claim["text"] in approved
    # Krish's brain is untouched: still both voices, still Krish deciding
    k = br.load(taste)
    assert br.recount(k)[("vocal", "vocal_chops")]["both_ways"] and "## Waiting for" not in br.render(k)[0]
    br.propose(k, MONDAY)
    assert "## Waiting for Krish" in br.render(k)[0] and "--taste" not in br.render(k)[0]


def test_trend_needs_a_span_of_adding_dates(taste):
    b = br.load(taste)
    for i, t in enumerate(b.tracks):
        t["added_at"] = f"2026-11-14T23:{i:02d}:00Z"  # a playlist built in one evening
    assert all(p["trend"] is None for p in br.recount(b).values())
    for i, t in enumerate(b.tracks):
        t["added_at"] = f"{2014 + i}-01-01T00:00:00Z"
    assert br.recount(b)[("groove", "tempo_118_125")]["trend"] == "falling"  # 122 BPM early, 100 BPM late


def test_calvin_brain_is_valid():
    b = br.load(REPO_TASTE / "calvin")
    assert br.check(b) == []
    assert br.voices(b) == ["calvin"] and br.decider(b) == "Calvin"
    assert all(c["evidence"] for c in b.claims)
