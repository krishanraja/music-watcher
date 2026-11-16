"""New track or new version: the parser on real name shapes (with invented titles) and the matcher."""
import pytest

from trackcard.engine import names

NOV13 = "2026-11-13T20:39:35Z"
NOV5 = "2026-11-05T17:42:28Z"
OCT22 = "2026-10-22T13:11:29Z"


@pytest.mark.parametrize("name,btime,title,date,src,note,version,copy", [
    ("Sunrise 11.13 .wav", NOV13, "Sunrise", "2026-11-13", "name", "", None, None),
    ("Sunrise 11.5 edits.wav", NOV5, "Sunrise", "2026-11-05", "name", "edits", None, None),
    ("Sunrise (1).wav", OCT22, "Sunrise", "2026-10-22", "upload", "", None, 1),
    ("late night beat v3.wav", OCT22, "late night beat", "2026-10-22", "upload", "", 3, None),
    ("tango beatv2 (2).wav", OCT22, "tango beat", "2026-10-22", "upload", "", 2, 2),
    ("sunrise_latest.wav", NOV13, "sunrise", "2026-11-13", "upload", "latest", None, None),
    ("tango_beat_v2.wav", NOV13, "tango beat", "2026-11-13", "upload", "", 2, None),
    ("Sunrise 11.20 v2.wav", "2026-11-20T10:00:00Z", "Sunrise", "2026-11-20", "name", "", 2, None),
    ("Sunrise master 12.1.wav", "2026-12-01T10:00:00Z", "Sunrise", "2026-12-01", "name", "master", None, None),
    ("Sunrise_11-13.wav", NOV13, "Sunrise", "2026-11-13", "name", "", None, None),
    ("Sunrise (Calvin edit) 11.14.wav", "2026-11-14T10:00:00Z", "Sunrise", "2026-11-14", "name", "calvin edit", None, None),
    ("Sunrise 2026-11-20.wav", "2026-11-21T10:00:00Z", "Sunrise", "2026-11-20", "name", "", None, None),
    ("Sunrise [2026-11-20 101500].wav", "2026-11-21T10:00:00Z", "Sunrise", "2026-11-20", "name", "", None, None),
    ("2 AM 11.5.wav", NOV5, "2 AM", "2026-11-05", "name", "", None, None),
    ("Final Hour 11.5.wav", NOV5, "Final Hour", "2026-11-05", "name", "", None, None),
    ("Remix Culture.aif", NOV5, "Remix Culture", "2026-11-05", "upload", "", None, None),
    ("Copy of Sunrise 11.13.mp3", NOV13, "Sunrise", "2026-11-13", "name", "", None, None),
    ("Sunrise version 2.wav", NOV13, "Sunrise", "2026-11-13", "upload", "", 2, None),
    ("Sunrise 124bpm 6A final.wav", NOV13, "Sunrise", "2026-11-13", "upload", "final", None, None),
    ("Café Sol 11.13.wav", NOV13, "Cafe Sol", "2026-11-13", "name", "", None, None),
])
def test_parse_shapes(name, btime, title, date, src, note, version, copy):
    p = names.parse(name, btime)
    assert (p.title, p.date, p.date_source, p.note, p.version, p.copy) == (title, date, src, note, version, copy)
    assert p.ask is None


def test_month_day_is_read_first_and_the_year_follows_the_upload():
    assert names.parse("Sunrise 5.11.wav", NOV13).date == "2026-05-11"  # M.D, not 5 November
    assert names.parse("Sunrise 3.4.wav", NOV13).date == "2026-03-04"
    assert names.parse("Sunrise 25.10.wav", NOV13).date == "2026-10-25"  # first number over 12: D.M
    assert names.parse("Sunrise 12.30.wav", "2027-01-02T10:00:00Z").date == "2026-12-30"  # last year's December
    assert names.parse("Sunrise 11.14.wav", NOV13).date == "2026-11-14"  # a day after upload is fine (time zones)


def test_empty_and_placeholder_titles_are_questions():
    assert names.parse("11.5.wav", NOV5).ask
    assert names.parse("Untitled 11.5.wav", NOV5).ask
    assert names.parse("Track 7 v2.wav", NOV5).ask
    assert names.parse("Audio 1.wav", NOV5).ask


def test_lossless_and_by_hint():
    assert names.parse("Sunrise.flac", NOV5).lossless and not names.parse("Sunrise.mp3", NOV5).lossless
    assert names.parse("Sunrise krish 11.5.wav", NOV5).by_hint == "krish"


def test_decide_version_new_ask_and_aliases():
    p = names.parse("Sunrise 11.20.wav", NOV13)
    assert names.decide(p, "v1", {"sunrise"}, {}).kind == "version"
    assert names.decide(p, "v1", {"moonset"}, {}).kind == "new"
    close = names.decide(names.parse("Sunrize 11.20.wav", NOV13), "v1", {"sunrise"}, {})
    assert close.kind == "ask" and close.candidates == ("sunrise",)
    sub = names.decide(names.parse("Sunrise Remix 11.20.wav", NOV13), "v1", {"sunrise"}, {})
    assert sub.kind == "ask"
    # only a generic word in common: a different track
    assert names.decide(names.parse("tango beat.wav", NOV13), "v1", {"late-night-beat"}, {}).kind == "new"
    # aliases win, by version id or by slug
    assert names.decide(close and names.parse("Sunrize 11.20.wav", NOV13), "v1", {"sunrise"},
                        {"v1": {"project": "sunrise"}}).kind == "version"
    assert names.decide(p, "v1", {"sunrise"}, {"sunrise": {"project": "dawn"}}) == names.Decision("new", "dawn", "aliases.json")
    assert names.decide(p, "v1", {"sunrise"}, {"v1": {"ignore": True}}).kind == "ignore"
