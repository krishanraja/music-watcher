# Roadmap

**Status: proposed, my read (Claude's), 2026-11-16. Krish has not set or ordered it.** It follows from what he asked for on
2026-11-16 ("the brain will eventually inform the production engine. I will use Splice MCP, Ableton MCP, and Suno MCP
eventually ... in the future we can have a UI"), and from what the code can and cannot do today. The North Star is not set
([`NORTH_STAR.md`](NORTH_STAR.md)), so nothing here is ranked by a number yet; the first item that needs Krish is choosing one.

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
- Add "against the target" lines to the brief: where the latest version sits against each brain's measured target in
  `GENERATION.md` (tempo, loudness, tonal balance, time to first peak). Evidence, not rules.
- **Done when:** a brief shows, for each gap, the rule (if any) that moved it up, and nothing else changes order.

## Phase 3: adapters (each behind its own yes)

| Adapter | Reads from `brief.json` | Does | Gate |
|---|---|---|---|
| **Splice** | `gaps[].splice` (describe_a_sound args), `stack_layer` | Searches loops per gap, builds a stack around a chosen loop | Searching is free; `download_asset` spends a credit: explicit yes per asset; no public links |
| **Ableton** | `context.tempo`, `bar1_s`, `sections`, `drops` | Sets tempo, drops locators at section and drop bars, names them | Runs on Krish's computer (Ableton is local); a session there, never from the worker |
| **Suno** | `context`, approved `rules` | Sketches a reference idea from the brief's tempo, key and approved style | Each generation spends credits: explicit yes; outputs are references, never their track |

- **Done when:** for one gap in one real brief, Claude runs the Splice search and Krish picks a sound that ends up in the next
  bounce, and the engine's next diff shows that gap closed.

## Phase 4: a UI

- A private page over `brief.json` and `STATUS.md`: projects, version timeline, what changed, gaps, questions to answer
  (writing `aliases.json` and accepting claims from the page instead of the command line).
- **Done when:** Krish and Calvin answer an engine question and accept a claim without a terminal.

## Open questions (Krish's)

- The North Star: what number says this repository is working? (Candidates, my read: bounces per month that close a measured
  gap; or time from a new bounce to an answered brief.)
- Should references also be measured with stems? It costs about 4 minutes per track on the worker and adds drops and stem
  shares to the references that fit.
- Should the sheet get a `Who` column, so a row needs no `Krish:` or `Calvin:` label?
- Should production records ever move to a private repository? Today they are public by Krish's choice (2026-11-16); audio,
  Drive links and emails never are.

## Known limits that shape the order

- trackcard measures; it does not hear (README, "Limits"). The brief says when a section label is only a cluster number.
- YouTube refuses datacenter machines, so some references are left for a home computer.
- The engine sees only what the worker's Drive login can see, and only files whose owner it can read.
