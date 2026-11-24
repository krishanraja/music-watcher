"""Command line: `trackcard analyze`, `mcp`, `brain`, `engine` and `studio`."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import click

from . import __version__
from .audio import TrackcardError


@click.group()
@click.version_option(__version__, prog_name="trackcard")
def main() -> None:
    """trackcard: listens to a WAV bounce and writes a track card an AI can read."""


@main.command()
@click.argument("path", type=click.Path(path_type=Path))
@click.option("--json", "json_too", is_flag=True, help="Also write <name>.trackcard.json.")
@click.option("--out", "out_dir", type=click.Path(path_type=Path, file_okay=False), default=None,
              help="Folder for the card (default: next to the WAV).")
@click.option("--no-stems", is_flag=True, help="Skip Demucs stem separation (much faster, less detail).")
@click.option("--sections", "sections_mode", type=click.Choice(["auto", "allin1", "laplacian"]), default="auto",
              show_default=True, help="Section method. auto = allin1 if installed, else Laplacian.")
@click.option("--print", "print_card", is_flag=True, help="Also print the card to stdout.")
@click.option("--bpm", type=float, default=None, help="Project tempo, if you know it. Overrides the measurement.")
@click.option("--key", "key", default=None, help="Key, if you know it: 'D minor', 'Dm', 'F# major', 'Bb' or '7A'.")
def analyze(path: Path, json_too: bool, out_dir: Path | None, no_stems: bool, sections_mode: str, print_card: bool,
            bpm: float | None, key: str | None) -> None:
    """Analyse PATH (a WAV bounce) and write <name>.trackcard.md."""
    from .card import to_markdown, write_card
    from .pipeline import analyze as run

    t0 = time.time()

    def progress(msg: str) -> None:
        click.echo(f"[{time.time() - t0:5.0f}s] {msg}...", err=True)

    try:
        card = run(path, sections_mode=sections_mode, stems=not no_stems, progress=progress, bpm=bpm, key=key)
        written = write_card(card, Path(path), out_dir, json_too)
    except TrackcardError as exc:
        click.echo(f"trackcard: error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:  # never fail silently
        click.echo(f"trackcard: unexpected error: {type(exc).__name__}: {exc}", err=True)
        sys.exit(2)
    for n in card.notes:
        click.echo(f"note: {n}", err=True)
    for p in written:
        click.echo(f"wrote {p}", err=True)
    if print_card:
        click.echo(to_markdown(card))


@main.command()
def mcp() -> None:
    """Run the MCP server on stdio (one tool: analyze_track)."""
    from .mcp_server import run

    run()


@main.group()
def brain() -> None:
    """The Music Brain: evidence -> patterns -> proposed rules -> approved rules (taste/brain/)."""


_TASTE = click.option("--taste", "taste_dir", type=click.Path(path_type=Path, file_okay=False), default=Path("taste"),
                      show_default=True, help="The taste/ folder.")


def _load(taste_dir: Path):
    from . import brain as br
    b = br.load(taste_dir)
    problems = br.check(b)
    if problems:
        for p in problems:
            click.echo(f"evidence problem: {p}", err=True)
        sys.exit(1)
    return br, b


@brain.command("check")
@_TASTE
def brain_check(taste_dir: Path) -> None:
    """Validate the evidence log against the vocabulary (quotes must match the words exactly)."""
    _, b = _load(taste_dir)
    click.echo(f"ok: {len(b.evidence)} evidence rows, {len(b.tracks)} playlist tracks, {len(b.claims)} claims")


@brain.command("render")
@_TASTE
def brain_render(taste_dir: Path) -> None:
    """Recount patterns and write taste/APPROVED.md and taste/brain/PATTERNS.md."""
    br, b = _load(taste_dir)
    br.write_views(b)
    click.echo("wrote APPROVED.md and brain/PATTERNS.md")


@brain.command("propose")
@_TASTE
def brain_propose(taste_dir: Path) -> None:
    """Propose this week's rules (at most the weekly budget in policy.json), freeze them, and re-render."""
    br, b = _load(taste_dir)
    new = br.propose(b)
    br.save(b)
    br.write_views(b)
    if not new:
        click.echo("nothing new to propose this week")
    for c in new:
        click.echo(f"proposed {c['id']}: {c['text']}")


def _decide(taste_dir: Path, claim_id: str, accept: bool, why: str) -> None:
    br, b = _load(taste_dir)
    try:
        c = br.decide(b, claim_id, accept, why)
    except br.BrainError as e:
        click.echo(f"error: {e}", err=True)
        sys.exit(1)
    br.save(b)
    br.write_views(b)
    click.echo(f"{c['id']}: {c['status']}")


@brain.command("accept")
@click.argument("claim_id")
@_TASTE
def brain_accept(claim_id: str, taste_dir: Path) -> None:
    """Accept a proposed rule; it moves into taste/APPROVED.md."""
    _decide(taste_dir, claim_id, True, "")


@brain.command("reject")
@click.argument("claim_id")
@click.option("--why", default="", help="Why it is wrong; kept with the claim.")
@_TASTE
def brain_reject(claim_id: str, why: str, taste_dir: Path) -> None:
    """Reject a proposed rule; it is never proposed again."""
    _decide(taste_dir, claim_id, False, why)


@main.group()
def engine() -> None:
    """The production engine: Drive in, measured productions and briefs out (engine/README.md)."""


_CONFIG = click.option("--config", "config_path", type=click.Path(path_type=Path, dir_okay=False), default=None,
                       help="Worker config (default: $ENGINE_CONFIG or ~/.music-watcher/engine.json).")
_LISTING = click.option("--listing", type=click.Path(path_type=Path, dir_okay=False), default=None,
                        help="Read a saved rclone lsjson listing instead of Drive (dry runs and tests).")
_CLONE = click.option("--clone", type=click.Path(path_type=Path, file_okay=False), default=None,
                      help="The repository checkout to read and write (default: the config's, else here).")


def _engine_setup(config_path, listing, clone):
    from .engine import config as ec
    from .engine.sources import FixtureSource, RcloneSource
    try:
        cfg = ec.load(config_path, clone=clone, require_drive=listing is None)
    except ec.ConfigError as e:
        click.echo(f"engine: {e}", err=True)
        sys.exit(2)
    return cfg, (FixtureSource(cfg, listing) if listing else RcloneSource(cfg))


@engine.command("plan")
@_CONFIG
@_LISTING
@_CLONE
def engine_plan(config_path, listing, clone) -> None:
    """Classify what is in Drive (new track, new version, question) without measuring or writing anything."""
    from .engine.run import plan_rows
    from .engine.sources import SourceError
    cfg, src = _engine_setup(config_path, listing, clone)
    try:
        rows, lst = plan_rows(cfg, src, cfg.clone)
    except SourceError as e:
        click.echo(f"engine: listing stopped: {e}", err=True)
        sys.exit(1)
    for r in sorted(rows, key=lambda r: (r.get("project") or "~", r["date"], r["name"])):
        extra = f" ({r['reason']})" if r.get("reason") else ""
        v = f" v{r['version']}" if r.get("version") else ""
        click.echo(f"{r['decision']:<12} {r.get('project') or '-':<22} {r['date']} ({r['date_source']}){v} "
                   f"note={r['note'] or '-'} folder={r['folder']} by={r['who']} key={r['key']}  {r['name']}{extra}")
    click.echo(f"{len(rows)} production file(s); {lst.ignored} file(s) of other kinds not read; "
               f"{lst.other_folders} in other subfolders; {sum(1 for i in lst.items if i.kind != 'audio')} inspiration item(s)")


@engine.command("run")
@_CONFIG
@_LISTING
@_CLONE
@click.option("--publish", is_flag=True, help="Reset the clone to main, then commit and push the rolling PR (worker).")
def engine_run(config_path, listing, clone, publish) -> None:
    """Measure new bounces and drops, write briefs and STATUS, and (with --publish) update the engine's PR."""
    from .engine.run import Engine, locked
    from .engine.words import words_stage
    cfg, src = _engine_setup(config_path, listing, clone)
    try:
        with locked(cfg):
            res = Engine(cfg, src).run(publish=publish, words=words_stage)
    except RuntimeError as e:
        click.echo(f"engine: {e}", err=True)
        sys.exit(1)
    click.echo(f"measured {len(res.measured)}; wrote {len(set(res.written))} file(s)")
    sys.exit(res.code)


@engine.command("resume")
@_CONFIG
def engine_resume(config_path) -> None:
    """Clear a pause (after a PR was closed without merging, or someone else committed to the engine's branch)."""
    from .engine import config as ec
    from .engine.run import resume
    click.echo(resume(ec.load(config_path, require_drive=False)))


# ---------------------------------------------------------------- the Studio (engine/STUDIO.md)

@main.group()
def studio() -> None:
    """The Studio: tool moves for a brief, and what people picked (Splice, Suno, Epidemic Sound, Spotify)."""


_REPO = click.option("--clone", type=click.Path(path_type=Path, file_okay=False), default=Path("."), show_default=True,
                     help="The repository checkout.")
_ON = click.option("--on", "on", default=None, help="Date, YYYY-MM-DD (default: today).")


def _today(on: str | None) -> str:
    import datetime as dt
    return on or dt.date.today().isoformat()


def _brief(clone: Path, slug: str) -> dict:
    import json
    f = clone / "engine" / "productions" / slug / "brief.json"
    if not f.exists():
        click.echo(f"studio: no brief for {slug!r} ({f}); the engine writes it", err=True)
        sys.exit(2)
    return json.loads(f.read_text(encoding="utf-8"))


def _card(clone: Path, vid: str) -> dict:
    import json
    f = clone / "engine" / "productions" / "cards" / f"{vid}.trackcard.json"
    if not f.exists():
        click.echo(f"studio: no card for version {vid}", err=True)
        sys.exit(2)
    return json.loads(f.read_text(encoding="utf-8"))


def _write_checked(path: Path, obj) -> None:
    """Write a committed Studio file only if the privacy gate passes it."""
    import json
    from .engine import privacy
    text = json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    hits = privacy.scan(text)
    if hits:
        click.echo("studio: refused by the privacy gate: " + ", ".join(sorted(set(hits))), err=True)
        sys.exit(3)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    click.echo(f"wrote {path}", err=True)


@studio.command("moves")
@click.argument("slug")
@_REPO
@click.option("--owner", type=click.Choice(["krish", "calvin"]), default=None,
              help="Whose next move it is (default: the latest bounce's uploader). Only their brain's rules are used.")
@click.option("--json", "as_json", is_flag=True, help="Print the moves as JSON.")
def studio_moves(slug, clone, owner, as_json) -> None:
    """List a project's moves: free ones first, then the standing yes, then the ones that spend credits."""
    import json
    from .studio import moves as mv
    ms = mv.plan_moves(_brief(clone, slug), owner=owner)
    if as_json:
        click.echo(json.dumps(ms, indent=1, ensure_ascii=False))
        return
    for m in ms:
        gap = f" {m['gap']['layer']} bars {m['gap']['bars']}" if m.get("gap") else ""
        click.echo(f"{m['id']}  {m['kind']:<17} {m['gate']:<12}{gap}  {m['why']}")


@studio.command("ear")
@click.argument("slug")
@click.option("--analysis", type=click.Path(path_type=Path, dir_okay=False, exists=True), required=True,
              help="Suno's audio-analysis JSON for the bounce (kept outside the repository).")
@click.option("--version", "vid", default=None, help="The version analysed (default: the brief's latest).")
@_REPO
@_ON
def studio_ear(slug, analysis, vid, clone, on) -> None:
    """Set Suno's analysis of a bounce against its card; write engine/productions/<slug>/ear/<version>.json."""
    import json
    from .studio import second_ear as se
    vid = vid or _brief(clone, slug)["latest_version"]
    rec = se.record(_card(clone, vid), json.loads(analysis.read_text(encoding="utf-8")), vid, _today(on))
    _write_checked(clone / "engine" / "productions" / slug / "ear" / f"{vid}.json", rec)
    for q in rec["questions"]:
        click.echo(f"ear-check: {q['text']}")
    if not rec["questions"]:
        click.echo("Suno and trackcard agree on everything they both read.")
    if rec["unread"]:
        click.echo("not read from Suno's answer: " + ", ".join(rec["unread"]))


@studio.command("twin")
@click.argument("slug")
@click.option("--recording", type=click.Path(path_type=Path, dir_okay=False, exists=True), required=True,
              help="The Epidemic recording as SearchRecordings returned it (JSON with id, title, credits).")
@click.option("--full", "full_card", type=click.Path(path_type=Path, dir_okay=False, exists=True), required=True,
              help="trackcard JSON card of the full-mix preview.")
@click.option("--stem", "stems", multiple=True, required=True,
              help="NAME=CARD for each stem preview, e.g. bass=bass.trackcard.json (drums, bass, melody, instruments, vocals).")
@click.option("--reference", default=None, help="The Spotify track id of the reference this twin stands next to.")
@_REPO
def studio_twin(slug, recording, full_card, stems, reference, clone) -> None:
    """Measure-based twin: write engine/productions/<slug>/twins/<recording id>.json."""
    import json
    from .studio import twin as tw
    rec = json.loads(recording.read_text(encoding="utf-8"))
    rec = rec.get("recording", rec)
    artists = ", ".join(c["artist"]["name"] for c in rec.get("credits") or [] if c.get("role") == "MAIN_ARTIST")
    stem_cards = {}
    for s in stems:
        name, _, f = s.partition("=")
        if name.lower() not in ("drums", "bass", "melody", "instruments", "vocals") or not f:
            click.echo(f"studio: --stem takes NAME=CARD with a stem name Epidemic uses: {s!r}", err=True)
            sys.exit(2)
        stem_cards[name.lower()] = json.loads(Path(f).read_text(encoding="utf-8"))
    ref = None
    if reference:
        b = _brief(clone, slug)
        r = next((r for r in b.get("references") or [] if r.get("id") == reference), None)
        if r is None:
            click.echo(f"studio: {reference} is not among {slug}'s references that fit (brief.json references)", err=True)
            sys.exit(2)
        ref = {"id": reference, "title": r.get("title"), "artists": r.get("artists")}
    out = tw.twin_record({"id": rec["id"], "title": rec.get("title"), "artists": artists or None},
                         json.loads(full_card.read_text(encoding="utf-8")), stem_cards, ref)
    _write_checked(clone / "engine" / "productions" / slug / "twins" / f"{rec['id']}.json", out)


@studio.command("cut")
@click.option("--card", "card_path", type=click.Path(path_type=Path, dir_okay=False, exists=True), required=True,
              help="trackcard JSON card of the licensed track (measured with stems for real drops).")
@click.option("--length", "length_s", type=float, required=True, help="Length of the video edit, seconds.")
@click.option("--hit", "hit_s", type=float, required=True, help="Where in the edit the drop must land (the reveal), seconds.")
@click.option("--recording-id", default=None, help="The Epidemic recording id (UUID).")
@click.option("--drop", "which", default="main", show_default=True, help="main, or bar:N for another drop or section.")
@click.option("--lead-bars", default=4, show_default=True, help="Bars of build kept before the drop.")
@click.option("--after-bars", default=4, show_default=True, help="Bars kept after the drop.")
@click.option("--format", "audio_format", type=click.Choice(["WAV", "MP3"]), default="WAV", show_default=True)
def studio_cut(card_path, length_s, hit_s, recording_id, which, lead_bars, after_bars, audio_format) -> None:
    """Drop on the cut: print Epidemic EditRecording arguments that land the measured drop on the reveal."""
    import json
    from .studio import cut
    try:
        out = cut.edit_input(json.loads(card_path.read_text(encoding="utf-8")), length_s, hit_s, recording_id, which,
                             lead_bars, after_bars, audio_format)
    except cut.CutError as e:
        click.echo(f"studio: {e}", err=True)
        sys.exit(2)
    click.echo(out["explain"], err=True)
    click.echo(json.dumps(out["args"], indent=1))


@studio.command("record")
@click.argument("slug")
@click.option("--move", "move_id", required=True, help="The move id from the brief (or `trackcard studio moves`).")
@click.option("--who", type=click.Choice(["krish", "calvin"]), required=True, help="Who chose.")
@click.option("--pick", default=None, help="provider:catalog-id, e.g. splice:<asset uuid> or epidemic:<recording id>; "
              "none: when nothing fit.")
@click.option("--suno-clip", default=None, help="A Suno clip id: only its hash is written, never the id.")
@click.option("--title", default=None, help="The picked sound's name, as the catalog shows it.")
@click.option("--credits", type=float, default=None, help="Credits this pick spent.")
@click.option("--note", default="", help="Why, in a few words.")
@_REPO
@_ON
def studio_record(slug, move_id, who, pick, suno_clip, title, credits, note, clone, on) -> None:
    """Record what a person picked from a move, in engine/productions/<slug>/moves.jsonl."""
    from .studio import ledger as lg
    from .studio import moves as mv
    b = _brief(clone, slug)
    m = next((m for m in mv.plan_moves(b, owner="krish") + mv.plan_moves(b, owner="calvin") if m["id"] == move_id), None)
    if m is None:
        click.echo(f"studio: no move {move_id} in {slug}'s brief", err=True)
        sys.exit(2)
    if bool(pick) == bool(suno_clip):
        click.echo("studio: give one of --pick or --suno-clip", err=True)
        sys.exit(2)
    if suno_clip:
        p = {"provider": "suno", "hash": lg.private_hash(suno_clip)}
    elif pick == "none":
        p = {"provider": "none"}
    else:
        prov, _, cid = pick.partition(":")
        p = {"provider": prov, "id": cid}
    if title:
        p["title"] = title
    row = {"move": move_id, "kind": m["kind"], "version": b["latest_version"], "pick": p, "who": who, "on": _today(on),
           "gap": m.get("gap")}
    if credits is not None:
        row["credits"] = credits
    if note:
        row["note"] = note
    try:
        added = lg.append(lg.path_for(clone, slug), row)
    except lg.LedgerError as e:
        click.echo(f"studio: {e}", err=True)
        sys.exit(2)
    click.echo("recorded" if added else "already recorded")


@studio.command("score")
@_REPO
@click.option("--json", "as_json", is_flag=True)
def studio_score(clone, as_json) -> None:
    """The North Star (Krish, 2026-11-24): gaps closed per bounce, and how many after a Studio pick."""
    import json
    from .studio import ledger as lg
    reg_f = clone / "engine" / "productions" / "registry.json"
    reg = json.loads(reg_f.read_text(encoding="utf-8")) if reg_f.exists() else {"projects": {}}
    sc = lg.score(reg, clone / "engine" / "productions" / "cards", clone)
    if as_json:
        click.echo(json.dumps(sc, indent=1))
        return
    if not sc["bounces"]:
        click.echo("gaps closed per bounce: not measured yet (needs two versions of a project, both measured with stems)")
        return
    click.echo(f"gaps closed per bounce: {sc['per_bounce']} ({sc['gaps_closed']} over {sc['bounces']} bounce(s); "
               f"{sc['studio_closed']} after a Studio pick)")


@studio.command("revealed")
@click.option("--who", type=click.Choice(["krish", "calvin"]), required=True,
              help="Whose Spotify was read. Their list feeds their own brain only.")
@click.option("--rows", "rows_path", type=click.Path(path_type=Path, dir_okay=False, exists=True), required=True,
              help="JSON list of {link, title, artists, rank_band}; rank_band is top50 or top200.")
@_REPO
def studio_revealed(who, rows_path, clone) -> None:
    """Write engine/references/<who>/revealed.csv: links, titles, artists and a rank band, nothing else."""
    import json
    from .studio import revealed as rv
    try:
        p = rv.write(clone, who, json.loads(rows_path.read_text(encoding="utf-8")))
    except rv.RevealedError as e:
        click.echo(f"studio: {e}", err=True)
        sys.exit(2)
    click.echo(f"wrote {p} ({len(rv.read(clone, who))} tracks)")


if __name__ == "__main__":
    main()
