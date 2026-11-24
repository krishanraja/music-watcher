# Roadmap

**Status: proposed, my read (Claude's), 2026-11-16; Phase 3 rebuilt as the Studio on 2026-11-24 at Krish's request.
Krish has not ordered the phases.** The North Star is set (Krish, 2026-11-24): gaps closed per bounce. It follows from what he asked for on
2026-11-16 ("the brain will eventually inform the production engine. I will use Splice MCP, Ableton MCP, and Suno MCP
eventually ... in the future we can have a UI"), and from what the code can and cannot do today. The North Star
([`NORTH_STAR.md`](NORTH_STAR.md)) is gaps closed per bounce, so the phases that close gaps rank first.

Each phase ends in something observable. A phase that sends, publishes, spends (Splice credits, Suno generations) or
changes access needs Krish's yes at that moment; nothing here grants it.

## Where it is (2026-11-16)

| Built and tested | Not yet running or proven |
|---|---|
| trackcard: cards with sections, stems, drops, bands, loudness, Splice brief; CLI and MCP | the engine on the worker (config, timer) |
| Two Music Brains with evidence, recounted patterns, frozen weekly proposals, approved rules | the first real engine cycle: Closure's 3 versions measured with stems |
| The production engine: Drive intake, new track vs new version, version diffs, briefs, privacy gate, rolling PR | Splice, Ableton and Suno acting on a brief |
| Inspiration drops and the reasons sheet feeding the right brain | a UI |
| `brief.json` shaped for the adapters (schema_version 1) | any accepted rule in Calvin's brain |

## Phase 0: switch it on (days)

- On the worker: write the engine config, run `trackcard engine plan`, enable `music-engine.timer` and disable
  `music-inspo.timer` in the same step ([`engine/README.md`](../engine/README.md), Worker setup).
- **Done when:** the engine's first PR holds Closure's three measured versions and their brief, the two archived beats,
  and a STATUS with no surprises; Krish merges it.
- Then: remove `taste/inspo/watch.py` once Krish approves (it can still commit a Drive id while its timer runs).

## Phase 1: trust the measurements (one or two weeks)

- Krish and Calvin ear-check the Closure brief: are the main drop, the build and the "what changed" lines right? Record
  their answers in `taste/ear-checks.json` so `pytest -m slow` holds trackcard to them.
- Calvin decides his three open proposals; Krish runs the weekly `propose` for both brains.
- Give known tempo and key per project through `aliases.json` (`"bpm"`, `"key"`), so bar numbers match the DAW.
- **Done when:** the brief's bar numbers and drop match what they hear, on at least two bounces.

## Phase 2: the brain informs the engine

- Rank a brief's gaps by the approved rules of whoever owns the next move (for example, a bass gap first when "growly,
  characterful bass" is approved), and say which rule ranked it. Only accepted claims; one brain's rules never applied as
  the other's.
- Built 2026-11-24: "against the target" lines in the brief (`targets`), recomputed from each brain's measured playlist
  (tempo, loudness, crest, sub and air balance, bars before the first full-energy section). Evidence, not rules.
- Built 2026-11-24: Splice character searches carry the words of the move owner's accepted rules only, filtered by key.
- **Done when:** a brief shows, for each gap, the rule (if any) that moved it up, and nothing else changes order.

## Phase 3: the Studio (built 2026-11-24; [`engine/STUDIO.md`](../engine/STUDIO.md))

Krish asked on 2026-11-24 to connect Suno, Splice, Epidemic and Spotify "without losing sight of what we built for what
purpose". The Studio is a third layer after the brains and the engine: `brief.json` carries `moves`, a session runs them,
and `moves.jsonl` records what a person picked, so the next diff credits the pick that closed a gap.

| Move | Tool | Does | Gate |
|---|---|---|---|
| Second ear | Suno upload + analysis | Checks the brief's tempo, key, bar grid and sections; disagreements become ear-checks | Standing yes for every new bounce (Ruling, Krish, 2026-11-24) |
| Splice search | Splice | Plain query per gap, then the owner's character words filtered by key | Free; downloads 1 credit each, asked |
| Notes, not sounds | Suno audio-create + audio-midi; sounds-create | 8-bar sketches at the project's tempo and key, transcribed to MIDI; or a loop | Credits each time, asked |
| Pro twin | Epidemic search + stem previews | When a finished catalog track brings in each layer, against ours | Free |
| Drop on the cut | Epidemic EditRecording | Lands a licensed track's measured drop on a video's reveal (content engine) | Own channels only; asked |
| Revealed taste | Spotify (read) | A person's most-played tracks count in their own brain's measured layer | Read-only; Krish's file holds links and rank bands only |
| **Ableton** | Ableton MCP | Tempo and locators from `context` | Still to build: runs on Krish's computer, never the worker |

- **Done when:** for one gap in one real brief, a session runs the Splice search (or a sketch), Krish or Calvin picks, the
  pick is recorded, and the engine's next diff shows that gap closed with `closed_by` naming the pick. Needs Phase 0 first.

## Phase 4: a UI

- A private page over `brief.json` and `STATUS.md`: projects, version timeline, what changed, gaps, questions to answer
  (writing `aliases.json` and accepting claims from the page instead of the command line).
- **Done when:** Krish and Calvin answer an engine question and accept a claim without a terminal.

## Open questions (Krish's)

- Answered 2026-11-24: the North Star is gaps closed per bounce. Still open: its target.
- Should references also be measured with stems? It costs about 4 minutes per track on the worker and adds drops and stem
  shares to the references that fit.
- Should the sheet get a `Who` column, so a row needs no `Krish:` or `Calvin:` label?
- Should production records ever move to a private repository? Today they are public by Krish's choice (2026-11-16); audio,
  Drive links and emails never are.

## Known limits that shape the order

- trackcard measures; it does not hear (README, "Limits"). The brief says when a section label is only a cluster number.
- YouTube refuses datacenter machines, so some references are left for a home computer.
- The engine sees only what the worker's Drive login can see, and only files whose owner it can read.
