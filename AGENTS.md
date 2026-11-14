# Working in music-watcher

This repo is Krish's Music Brain: `trackcard` (src/) measures audio locally, and `taste/` holds what he and Calvin like,
including the playlist knowledge graph (`taste/graph/`, start with `GENERATION.md`).

`NOW.md` says where it stands. It runs on the worker server (`trackcard` and the Music Inspo watcher), and the fleet's record of that move is ai-harness `state/vps/MIGRATION-2026-11-14.md`.

<!-- north-star:start -->
## North Star: read it first, every session

[`docs/NORTH_STAR.md`](docs/NORTH_STAR.md). It is not set yet: only Krish sets it. Say which part of it a task moves before starting, and close by noting what moved. The state line, the first line under "Where it is right now" in `NOW.md`, says U4 until he sets a number ([the harness contract](https://github.com/krishanraja/ai-harness/blob/main/contract/north-star-metric.md)).
<!-- north-star:end -->

## Close out

Before a session that changed the repository ends, write `now-notes/YYYY-MM-DD-<slug>.md` with `Status:`, `Next:` (the single next action) and the line `North Star check (YYYY-MM-DD): holds.` with nothing in front of it. It folds into `NOW.md` on the default branch.

## Getting audio and media: use content-watcher

Whenever a task needs audio, video or a post's media that is not already a local file (a YouTube video, a TikTok,
an Instagram reel, a SoundCloud or Spotify-linked track, a DJ set, a live clip), use
[krishanraja/content-watcher](https://github.com/krishanraja/content-watcher) to get it rather than writing a new fetcher:
`content-watch fetch <url>` for the media, `content-watch audio <file> --format wav` for a WAV that trackcard can read.
Its `docs/FALLBACKS.md` lists every route per platform.

- YouTube refuses cloud machines. On a cloud session, try SoundCloud first (`yt-dlp "scsearch5:<artist> <title>"`, accept
  only a hit within 6 s of the Spotify length), then hand the rest to a home computer, where content-watcher's YouTube route
  (yt-dlp with Deno and the bgutil token helper) works. Say plainly which tracks were left for home.
- Measure the full track, never a 30 s preview, when the question is about arrangement: progressive house progresses.
  A preview is a labelled fallback only.
- Never commit audio. Keep it outside the repo and delete it once its `.trackcard.json` exists if disk is tight.

## Provenance

Every taste claim says where it came from: said by Krish or Calvin, measured by trackcard (full track or preview), read from
a metadata source (Spotify, Discogs, label page), or inferred by Claude. Inferred lines say "my read".

## The Music Brain (taste/brain/)

- Rules a generator or Splice search may follow live only in `taste/APPROVED.md`. Everything else in `taste/` is evidence or
  a pattern, and decides nothing on its own.
- When Krish or Calvin says something about a track in a session, append it to `taste/brain/evidence.jsonl`: their words whole,
  where and when said, and signals from `taste/brain/vocab.json` whose quotes appear character for character in the words.
  Never write measured evidence there; it is derived from `taste/graph/tracks.csv`. A word that is not in the vocabulary goes
  in as `other/<word>`; the vocabulary grows only by a change Krish merges.
- Taken back? Set `"withdrawn": true` on the row; never delete it. Run `trackcard brain check` after any edit.
- Weekly: `trackcard brain propose` (at most 3, frozen once proposed). Krish runs `trackcard brain accept|reject <id>`.
- After any change to evidence, claims or the graph: `trackcard brain render`.

## The worker: use it by default

Krish has an always-on Linux server, **the worker** (`ssh worker`; x86 Ubuntu, 4 vCPU / 8 GB). `trackcard` is
installed there with the `stems` (Demucs, CPU) and `loudness` extras, so use it without being asked:

- **Already on it?** If `hostname` prints `worker`, you are a Remote Control or Codex session on it, running as
  `agent`. Clone into your own `~/work/music-watcher-<task>` folder and work there. `trackcard` and `content-watch`
  are already on your PATH; their installed copies are in `~/apps/` (pull to update, never edit in place).
- **On Krish's laptop?** Edit locally, but send heavy steps (stem separation and `trackcard analyze` on full tracks,
  the test suite) to the worker: `ssh worker offload <<'EOF'` … `EOF` runs as `agent` in `~/work` inside the worker's
  CPU and memory budget. Clone or pull into `~/work/music-watcher-<task>` first; delete it when done.
- **On a cloud session** (claude.ai/code, Codex cloud): the worker is unreachable, because outbound SSH is blocked
  there. Say so; don't try.
- **Audio on the worker lives in `~/media`**, outside every repository (never commit audio). Stems on CPU take
  about 3 to 4.5 minutes for a 4 to 5 minute track; the Demucs weights are already downloaded.
- **New drops in Drive › Inspiration › Music Inspo are measured automatically** on the worker every 15 minutes (`taste/inspo/watch.py`, how it works in `taste/inspo/README.md`); the cards arrive as one rolling PR, `inspo/new-drops`. Don't measure a Music Inspo drop by hand unless that PR says it was left for home.
- **The worker is a datacenter machine, so YouTube refuses it too.** The "Getting audio" rules above apply to it as
  they do to a cloud session: SoundCloud first, the rest to a home computer, and say which tracks were left for home.
- Never hand-copy a key onto the worker (its secrets live in a root-only store), and never copy `~/.codex/auth.json`.
