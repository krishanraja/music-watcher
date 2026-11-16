# The production engine (engine/)

Krish and Calvin make tracks together. The **brains** (`taste/`, `taste/calvin/`) hold what each of them likes. The
**engine** collects what they make and what they drop as inspiration, measures it with trackcard, and keeps one brief per
project that people, Claude, a later UI and the Splice, Ableton and Suno MCPs can work from. It reads the brains' approved
rules; it never decides one. Code: `src/trackcard/engine/`. Asked for by Krish on 2026-11-16.

## What goes in, what comes out

| In (Drive, read-only) | Out (this folder, through one PR) |
|---|---|
| **Music Production**: bounces (`.wav`, `.aif`, `.flac`, `.mp3`, ...), and `Archive/` | `productions/registry.json`: every project and version; `productions/cards/<version id>.trackcard.{json,md}`; `productions/<slug>/BRIEF.md` + `brief.json` |
| **Music Production › Inspiration**: `.txt` files or Docs holding a Spotify track link, and any words | `references/index.csv`, `references/cards/`, `references/<who>/tracks.csv` (the brain feed), words in `taste/brain/evidence.jsonl` |
| **The sheet** "Calvin and Krish - Spotify tracks" (in Inspiration) | words in `taste/brain/evidence.jsonl` under the voice that said them; references |
| | `STATUS.md`: projects, and what waits for a person |

Nothing else in Drive is read: other file kinds and other subfolders are counted in STATUS, never named.

## New track or new version

From the bounce's **name** and its **upload date** (`names.py`):

- A name reads `<title> [date] [notes] [vN] [(n)]`: `Closure 11.13 .wav`, `Closure 11.5 edits.wav`, `Closure (1).wav`,
  `satin jackets beat v3.wav`, `latin beatv2 (2).wav`. Dates are month.day (US style; day.month only when the first number
  is over 12), the year is the upload's. No date in the name: the upload date, and the brief says so.
- Same title -> a new version of that project. A close title (`Closure` vs `Closur`, or `Closure Remix`), an empty title or
  a placeholder title (`Untitled 11.5`, `Track 7`) -> a **question** in STATUS, not measured until answered.
- The same file uploaded twice -> `copy_of`, not measured. The same bounce as `.wav` and `.mp3` -> one version, the
  lossless file measured. A file replaced in place in Drive -> a new version (`<id>-r2`); the old card stays.
- **Latest** = the newest version outside `Archive/`. A project whose versions are all in `Archive/` is marked archived.

**Naming that always works:** `<Title> <month>.<day> [note].wav`, e.g. `Closure 11.20 drums.wav`.

**Answer a question, or correct anything,** in `productions/aliases.json`, keyed by the version id STATUS gives (or by a
title slug), e.g. `{"0c339e3b93eb": {"project": "closure", "date": "2026-11-20", "note": "drums", "by": "calvin"}}`.
`{"ignore": true}` drops a file; `"bpm"` and `"key"` are passed to trackcard when you know them. Aliases are re-applied on
every run, and never move or rewrite a card.

## The brief

`BRIEF.md`: where the project stands, what changed since the previous version (length, tempo, key, sections, loudness,
main drop, stems, Splice gaps closed and opened), the section map, gaps to fill, what each brain has approved, and
references that fit (within 3 BPM or half/double time and a Camelot neighbour, from the references and both playlists).
Stem-based changes are compared only when both versions were measured with stems; otherwise the brief says
"not comparable".

## Adapter contract (`brief.json`, schema_version 1)

Nothing calls the MCPs yet. When an adapter does:

- **Where to read:** `engine/productions/<slug>/brief.json` on the `engine/updates` branch while its PR is open, else on
  `main`. `latest_version` and `source_card` name the card behind it.
- **Splice:** each `gaps[].splice` is `{tool: "describe_a_sound", args: {query, bpm_min, bpm_max, type: "loop"}}`,
  matching the live tool's inputs (read 2026-11-16). `key_confirm_needed: true` means trackcard is unsure of the key: ask
  before searching by key. `stack_layer.layer_type` is the `update_stack` layer type. Search and build stacks with
  `generate_public_url: false`. **`download_asset` spends a credit: only after an explicit yes for that asset in that
  session.** No field here triggers a download or a share.
- **Ableton:** `context.tempo.bpm`, `context.bar1_s` (where bar 1 starts in the bounce), `context.sections[]` and
  `context.drops[]` with integer bars and seconds: tempo and locators. `context.drops` is null when stems were not
  measured.
- **Suno:** `context` (tempo, key) and the approved rules as style hints.
- **Rules:** `rules[]` is a pointer view per brain (`brain`, `decided_by`, `approved_md`, accepted claim ids and texts).
  Re-read that brain's `APPROVED.md` before acting; never apply one brain's rules as the other's, and never treat a
  proposal as a rule.

## Words and references

- **Sheet:** rows split by speaker (`Krish (20 Nov 2026): ... Calvin: ...`, or a `Who` column). A new voice on a track goes
  into the shared evidence log with `"added_by": "engine"`, its words exactly as typed and where they came from. The
  engine's first read is a baseline: everything already on the sheet then (undated, or dated on or before 2026-11-16) is
  recorded as seen and never written; the 2026-11-06 hand read (`taste/references.json`, now a frozen snapshot) covers the
  rows through 2026-11-06. After that, every new segment is considered. A segment with no date of its own takes the
  row's date only when it is the cell's only speaker.
- **Questions instead of guesses**, asked once in the PR: words with no speaker, words about the speaker in the third
  person, new words on a track that voice already has a row for (or a withdrawn row), and words holding any other link,
  an email or a phone number (never echoed).
- **Auto tags** come from `triggers.json` (my read, not Krish's): strength 1, `"tagged_by": "engine (triggers)"`, none
  under a negation, every one listed in the PR to confirm or retag. The vocabulary still grows only by Krish's merge.
- **Text drops:** words belong to whoever uploaded the file, and only when it holds one track link (any other link
  makes it a question). A `krish` or `calvin`
  word in the file name routes the reference (a drop made for the other person), never the words.
- **References:** every Spotify track from a drop or the sheet, measured once from SoundCloud within 6 s of Spotify's
  length (else left for a home computer; YouTube refuses the worker). A card already in `taste/cards/`, `taste/inspo/cards/`
  or a playlist graph is reused. References carry evidence ids, never words.
- **Brain feed:** only drops count in a brain's measured layer (`references/<who>/tracks.csv`, read through
  `measured_extra` in each `brain/policy.json`), never a track already in that person's playlist graph.

## Privacy (the repository is public)

The Drive files are link-shared, so a Drive file id is a working download link to an unreleased bounce, and a folder id
opens every bounce in it. The engine therefore:

- turns every listing entry into an allowlisted record at once: the id becomes a 12-character hash (the version id), the
  owner's email becomes `krish`, `calvin` or `unknown` and is dropped, descriptions are never read;
- names downloaded audio `<version id>.wav`, so no card carries a Drive name;
- writes failure reasons as fixed codes (`privacy.WHY`), never error text;
- runs a gate before every commit and push (`privacy.scan`) over the staged lines, commit message and PR text: any known
  id, folder id or email, any email address, Google Drive/Docs link, private SoundCloud link or phone number stops it.

If an id ever reaches GitHub anyway, restrict that file's sharing in Drive at once: a push cannot be taken back. Raw
`rclone lsjson` output and the worker journal never go into notes, PRs or chat.

## Running it

```bash
trackcard engine plan                 # what is in Drive and how each bounce is classified; measures and writes nothing
trackcard engine run                  # measure (at most max_per_run) and write, in the clone, without git
trackcard engine run --publish        # the worker's job: reset to main, run, privacy gate, one commit, one PR
trackcard engine resume               # after a pause (PR closed without merging, or someone else's commit on the branch)
trackcard engine plan --listing saved.listing.json --config cfg.json   # a dry run on a saved rclone listing
```

A run is a pure function of main, the Drive listing and the worker's cache of measured cards: the same inputs give the
same bytes, so an unchanged Drive opens no PR. Tries are counted before each measurement (3, then "gave up"), audio is
deleted after its card exists, and a lock stops two runs at once.

### Worker setup (Krish, or a worker session he starts)

1. **Its own clone**, separate from the Music Inspo watcher's, with the same git push and `gh` access, e.g.
   `~/engine/music-watcher`.
2. **Config** at `~/.music-watcher/engine.json` (outside the clone; never committed), from `config.example.json`: the
   Inspiration and Music Production folder ids, and `people` mapping each of Krish's and Calvin's Google account emails to
   `krish` or `calvin`.
3. **Check access:** `ENGINE_CONFIG=~/.music-watcher/engine.json trackcard engine plan` must list the bounces. The worker's
   rclone login must see the Music Production folder (it belongs to Krish's personal Google account), and rclone must be
   recent enough to return owner and created-time metadata: the engine stops with `metadata_missing` if not.
4. **Units** (as the service user; adjust paths), and in the same step disable the Music Inspo watcher (Krish's ruling,
   2026-11-16):

```ini
# /etc/systemd/system/music-engine.service
[Unit]
Description=music-watcher production engine (one run)
After=network-online.target
[Service]
Type=oneshot
User=<service user>
Environment=ENGINE_CONFIG=/home/<service user>/.music-watcher/engine.json
Environment=PYTHONPATH=/home/<service user>/engine/music-watcher/src
WorkingDirectory=/home/<service user>/engine/music-watcher
ExecStart=<trackcard venv>/bin/python -m trackcard.cli engine run --publish
TimeoutStartSec=5400

# /etc/systemd/system/music-engine.timer
[Timer]
OnCalendar=*:0/15
Persistent=true
[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl disable --now music-inspo.timer && sudo systemctl enable --now music-engine.timer
```

`PYTHONPATH` points at the clone's own `src/`, so the engine, the brain and `build_graph.py` always come from the same
commit as the data. The journal is `~/.music-watcher/engine/journal.log` (redacted, never committed).
