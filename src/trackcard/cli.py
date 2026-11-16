"""Command line: `trackcard analyze` and `trackcard mcp`."""

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


if __name__ == "__main__":
    main()
