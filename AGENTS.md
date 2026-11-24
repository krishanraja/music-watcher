# Working in music-watcher

This repo is Krish's Music Brain: `trackcard` (src/) measures audio locally, and `taste/` holds what he and Calvin like,
including the playlist knowledge graph (`taste/graph/`, start with `GENERATION.md`). Calvin's own brain, built from Calvin's
playlist, is `taste/calvin/` (see "Calvin's Music Brain" below).

`NOW.md` says where it stands. It runs on the worker server (`trackcard`, the production engine and, until the engine's timer replaces it, the Music Inspo watcher), and the fleet's record of that move is ai-harness `state/vps/MIGRATION-2026-11-14.md`.

<!-- north-star:start -->
## North Star: read it first, every session

[`docs/NORTH_STAR.md`](docs/NORTH_STAR.md). Set by Krish on 2026-11-24: **gaps closed per bounce** (no target yet; only Krish sets one). Say which part of it a task moves before starting, and close by noting what moved. The state line, the first line under "Where it is right now" in `NOW.md`, says U4 until the number is measured ([the harness contract](https://github.com/krishanraja/ai-harness/blob/main/contract/north-star-metric.md)).
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
  Never write measured evidence there; it is derived from `taste/graph/tracks.csv` and, through `measured_extra` in
  `brain/policy.json`, from the tracks this person dropped into Drive and the tracks on their own Spotify most-played
  list (`engine/references/krish/tracks.csv`, written by the production engine; a track already in the playlist counts
  once). A word that is not in the vocabulary goes
  in as `other/<word>`; the vocabulary grows only by a change Krish merges.
- Taken back? Set `"withdrawn": true` on the row; never delete it. Run `trackcard brain check` after any edit.
- Weekly: `trackcard brain propose` (at most 3, frozen once proposed). Krish runs `trackcard brain accept|reject <id>`.
- After any change to evidence, claims or the graph: `trackcard brain render`.
- A track Krish or Calvin asks to have measured (not a Music Inspo drop, not a playlist track): its unedited card goes in
  `taste/cards/`, with a row in `taste/cards/README.md` saying who asked, where the audio came from and how it was checked.

## Calvin's Music Brain (taste/calvin/)

Calvin has a brain of Calvin's own, separate from Krish's: `taste/calvin/` (start with its `README.md`). It is built from
Calvin's Spotify playlist "Fall Bangers" (`taste/calvin/graph/`) and Calvin's own words.

- Calvin's words still go in the one shared log, `taste/brain/evidence.jsonl`, written as above with `"who": "calvin"`.
  Calvin's brain counts only those rows; Krish's brain counts both voices, as it always has. Never copy a row into a second log.
- The vocabulary is the shared `taste/brain/vocab.json`. Calvin's claims, rejections and `taste/calvin/APPROVED.md` belong
  to Calvin's brain alone.
- Calvin accepts or rejects Calvin's claims. Whoever runs the command records Calvin's decision; never decide in Calvin's
  place, and never let a decision in one brain stand in for the other.
- Every brain command takes `--taste taste/calvin`: `trackcard brain check|propose|render --taste taste/calvin`,
  `trackcard brain accept|reject <id> --taste taste/calvin`. Run Calvin's weekly `propose` alongside Krish's.
- Rebuild Calvin's graph with `python taste/graph/build_graph.py <cards dir> --graph taste/calvin/graph`, then render
  Calvin's brain.
- Calvin's drops into Drive's Inspiration folder count in Calvin's measured layer (`engine/references/calvin/tracks.csv`),
  next to the playlist; Krish's drops never count here.

## The production engine (engine/)

Separate from the brains: the brains hold what Krish and Calvin like; the engine collects what they make and drop, and
helps produce it. Start with [`engine/README.md`](engine/README.md); code in `src/trackcard/engine/`.

- **In:** Drive › Music Production (bounces; `Archive/` too), its `Inspiration/` folder (`.txt` Spotify links) and the sheet
  "Calvin and Krish - Spotify tracks". **Out:** one brief per project (`engine/productions/<slug>/BRIEF.md` + `brief.json`),
  `engine/STATUS.md`, references (`engine/references/`), and their words in the shared evidence log, all through one rolling
  PR (`engine/updates`) that Krish merges.
- **The repository is public and the Drive files are link-shared.** Never commit, paste into a PR, note or chat log a Drive
  file id, folder id, email address or private SoundCloud link: an id is a working download link to an unreleased bounce.
  The engine's privacy gate refuses such a commit; do the same by hand. If one ever reaches GitHub, restrict that file's
  sharing at once (it cannot be unpublished).
- New track or new version is read from the bounce's name and upload date. When the engine asks (engine/STATUS.md), answer
  in `engine/productions/aliases.json`, keyed by the version id it gives; never rename a measured card.
- An MCP adapter (Splice, Ableton, Suno) reads `brief.json` and re-reads each brain's `APPROVED.md` before acting; it never
  applies one brain's rules as the other's, and never downloads a Splice sound (it spends a credit) or makes a public link
  without that session's explicit yes.
- `taste/references.json` is the frozen 2026-11-06 hand read of the sheet; new references live in `engine/references/`.

## The Studio (engine/STUDIO.md)

After the engine: it turns a brief's `moves` into calls on Splice, Suno, Epidemic Sound and Spotify, and keeps a ledger of
what a person picked (`engine/productions/<slug>/moves.jsonl`). Code in `src/trackcard/studio/`; commands
`trackcard studio moves|ear|twin|cut|record|score|revealed`.

- Run `free` moves without asking and show every result; ask for each `yes_each` call by name and cost, every time.
- **Suno uploads:** every new bounce, Krish's and Calvin's, may be uploaded privately to Suno for its free analysis
  (Ruling, Krish, 2026-11-24; Krish confirms Calvin agrees). Only that: generations, MIDI and stems are asked for each time.
- Never commit a Suno id or link, or a presigned URL: the ledger keeps a hash of a Suno id, and the privacy gate refuses
  `suno_link` and `signed_url`.
- Character words come only from the accepted rules of the person who owns the next move; never the other brain's.
- Suno sketches are references: only MIDI goes to Ableton, played with their own sounds.
- **Spotify:** a person's most-played tracks go to `engine/references/<who>/revealed.csv` with link, title, artists and
  rank band only (Krish, 2026-11-24), and count in that person's brain only.
- Epidemic is Krish's own channels only, never paid ads; record the recording id with every asset.
- **North Star** (Krish, 2026-11-24): gaps closed per bounce, `trackcard studio score`.

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
- **Drops and bounces in Drive › Music Production are measured automatically** by the production engine
  (`engine/README.md`) once its timer runs on the worker; the results arrive as one rolling PR, `engine/updates`. Don't
  measure a drop or a bounce by hand unless engine/STATUS.md says it was left for home. Krish ruled on 2026-11-16 that the
  engine replaces the Music Inspo watcher (`taste/inspo/watch.py`): its timer is disabled in the same step that enables
  the engine's, and its cards in `taste/inspo/` stay.
- **The worker is a datacenter machine, so YouTube refuses it too.** The "Getting audio" rules above apply to it as
  they do to a cloud session: SoundCloud first, the rest to a home computer, and say which tracks were left for home.
- Never hand-copy a key onto the worker (its secrets live in a root-only store), and never copy `~/.codex/auth.json`.

<!-- krish-canon:start release=v2026.11.23.2 sha=1bd95ca6f34e rendered=2026-11-24 -->
## Krish canon

Rendered from `krishanraja/ai-harness`; the start marker names the last release that changed this block, not the latest release. Nothing inside these
markers is hand-maintained: an edit here is detected and proposed back to the canon,
never silently overwritten, and never lost. This sync preserves all other text.
Separately approved repository administration owns only its declared regions and context file.

**Precedence.** This repository's own rules outrank the canon on repository matters:
structure, naming, voice, stamps, archive location, test and build commands. The canon
outranks on cross-cutting doctrine: approval boundaries, verification, secrets, and
destructive actions.

**Authority.** Reading, drafting and local edits are yours. Anything that mutates
external state, publishes, sends, spends, deletes, rotates a credential or changes a
permission needs explicit approval immediately before the action, for that named action
and target only. Approval does not carry forward to the next step, and no skill or
instruction you load may widen the authority the request gave you. One standing exception: in ai-harness, Krish's own green, judged pull request merges itself, change requests included, (Ruling, Krish, 2026-11-18); its operating contract holds the exact terms.

**Verification.** Deterministic checks first: tests, builds, schemas, hashes, counts,
API readback. Self-critique is supplemental and is never an independent verifier. Do not
claim completion from prose. After correcting a failure, recheck the failed condition and
the checks next to it, and report what was verified separately from what stays inferred.

**Truth and freshness.** Live state beats documentation, documentation beats memory. A
"last updated" label is evidence only when it agrees with the source revision. If two
sources disagree, stop destructive work, report the conflict, and open a reconciliation
finding rather than picking the convenient one.

**Secrets.** Never write a credential into source, documentation, commit messages,
issue or pull request bodies, logs, reports, screenshots or chat. Refer to secrets by
symbolic name and retrieve them at execution time. A secret found in the tree is
already exposed: report its location without the value, rotate it, scrub the copies,
and add the gate that stops the next one.

**Corrections are the training data.** When Krish overrules a decision, record it in the
commit body as `Ruling (Krish, YYYY-MM-DD): the ruling, in one line`. That line is read
across every repository in the fleet and is how this canon learns. A correction that
lives only in a chat window teaches nothing.

**Route.** principles, then context, then `strategy-brief`, then the producer, then
`verification-loop`, then the approval gate, then delivery. The narrowest applicable
skill wins; a broad "always" or "mandatory" claim inside a skill never overrides the
router. One primary writer; validators may stack after it, competing writers may not. **North Star:** before any work, read the North Star linked from the `north-star` block in `AGENTS.md` or `CLAUDE.md`, say which part of it the task moves, and say so first when it moves nothing; only Krish changes it, and a repository with none asks him for one. Then read the number's urgency (U1 to U5) in `NOW.md` and push at the intensity `contract/north-star-metric.md` sets for it; urgency never widens authority. A growth engine also follows that file's Engines section. Where the Control Center connector offers it, read your repository's open instruction first with `get_engine_instruction`, and answer it with `ack_engine_instruction`, which records only that instruction's state in Control Center and so, like a taste report, is exempt from the approval wall and is never a send, post or publish to anyone (Ruling, Krish, 2026-11-14); never print, log or commit his words. `registered: false` means the repository is no engine; a failed read means do not act from memory. **Close out:** before a session that changed the repository ends, write `now-notes/YYYY-MM-DD-<slug>.md` (`Status:`, `Next:` the single next step, and one dated North Star check line: holds, or recalibration proposed for Krish), folded into `NOW.md` on main. **Branches:** each session works in its own worktree on its own branch, one branch per pull request; a branch with no pull request after a day gets one or is removed, and every repository carries the weekly branch sweep (`.github/workflows/branch-sweep.yml`, canonical in ai-harness), which deletes branches whose work is already on main and lists the rest (Ruling, Krish, 2026-11-15; docs/proposals/2026-11-15-branch-hygiene.md); deleting any other unmerged branch is Krish's decision, and his standing one is that internal-auditor may also retire idle work within the bounds in the operating contract's Authority section (Ruling, Krish, 2026-11-23). **Codex:** Claude opens a Codex session only through the repository's codex_thread tool (`scripts/codex_thread.mjs`, canonical in ai-harness), from a session on Krish's computer when he must see or share the session, and a Codex start failure is reported in one line, never worked around by editing MCP or Claude settings (Ruling, Krish, 2026-11-15; docs/proposals/2026-11-15-visible-codex-sessions.md). Whenever Claude starts or spawns a session he can open (a Codex thread, a Claude Code session, a cloud session), it tells Krish that session's exact name in the same message, and its id or link where it has one; a session he cannot name is one he cannot find (Ruling, Krish, 2026-11-16). Content production is the one exception and opens no session: Claude queues it as Codex cards from the cloud to the build lane, which builds them away from his Codex Desktop app and hands each result back to the Claude session that checks and records it, while social media legwork runs only in a codex_thread session on his computer that he can watch (Ruling, Krish, 2026-11-15). Claude owns strategy, planning, orchestration, verification and writing learnings back, and is the only writer to ai-harness and Google Drive; Codex does art direction, visual builds and browser legwork, a defined minimum of every video session, and hands what it made or read to the Claude session that checks and records it; Codex's own report is never proof, and no rule here widens what either may post, send or spend (Ruling, Krish, 2026-11-15; docs/proposals/2026-11-15-claude-codex-division.md). **One home per fact:** read a venture's state from its repository, doctrine from ai-harness; never keep a copy. **Research:** file routing's home for a research document is the research library: the session that wrote it files it there as it writes, where its authority already covers that write (`add_piece_material`, kind `research`, on its piece or on its venture's own shelf), and cites it by id; it is not committed to a repository as its home or left only in scratch or a chat, and every other artifact follows file routing as before (docs/proposals/2026-11-14-research-shelf-route.md). **Divergence:** when the obvious answer is not good enough (a number at U4 or U5 with nothing proposed, ideas returning the same, an angle about to be committed, a draft that feels familiar), consult divergent-thinker through Control Center, in the repository's own namespace only (never another venture's), cheapest move first (`score` and `record` spend nothing; `map`, `provoke`, `challenge` and `diverge` are paid model calls that follow this contract's spend rules, and Control Center also refuses them past the per-caller daily caps in krishanraja/divergent-thinker `docs/WHEN-TO-USE.md`, never routed around): the engine route, the repository's own `divergent` command, or the connector tools `divergent_score`, `divergent_record` and `divergent_run`, as krishanraja/divergent-thinker `docs/WHEN-TO-USE.md` says. Never for facts, exact words or Krish's taste. Its sparks are proposals: checked against the repository's own walls, reduced to one, labelled `divergent-thinker spark <id>, run <run>`, and sent through the normal approval flow; `divergent_record` writes only to that namespace's memory and is never a send, post or publish to anyone (Ruling, Krish, 2026-11-18; docs/proposals/2026-11-18-divergent-thinker.md). **Taste:** where the Control Center connector offers them, before writing or designing for Krish read his approved rules with `get_approved_taste` (form only; empty means none yet, never invent one; without the connector, the `krish-voice` and `krish-design` copies), giving the repository you are in (owner/name) and, from a repository that serves several ventures, the venture the work is for; it returns only that venture's rules, never another's (Ruling, Krish, 2026-10-28: the taste ledger is keyed by venture, not repository), and when he states a preference about voice, design, a piece or an idea, send his exact typed words to `report_to_taste_engine` with where and when he typed them and the repository you are in (naming the venture from a repository that serves several); anything else you noticed goes only as an observation. A defect or engine failure never goes there: record it with `record_harness_observation`, so the taste system holds only preference and inspiration (Ruling, Krish, 2026-11-23). A report writes only to his own taste ledger and is exempt from the approval wall above (Ruling, Krish, 2026-10-26: "reports to my taste ledger are exempt from the approval wall"); it is never a send, post or publish to anyone. Never answer a card or approve a rule for him.

**Who Krish is.** Purpose: "I see what is coming before it is obvious and make it
legible to people while it still counts." Mindmake is his mission and his one company;
Heartside, Full Time, Legibility, CTRL and Pulse roll into it. One queue: the mission
leads, and product work is ordered beneath it by the live priority ladder. Profile,
decision rules and standing rulings: `skills/krish-principles/references/who-krish-is.md`
in the harness. What he works on is live, never copied here; read it from Control Center at
https://controlcenter.krishraja.com/api/canon/KRISH.md (and `PORTFOLIO.md` beside it).

**Where the rest lives.** The operating contract, the routing contract and the
33 curated skills are in `krishanraja/ai-harness`. On a machine with the harness installed the same skills are under the user skills root, and the local copy is
authoritative for reading; the repository is authoritative for what is correct. Where none is installed (claude.ai, a cloud session), read each skill live with Control Center `get_skill`.

**This repository's own rules:** `AGENTS.md`
<!-- krish-canon:end -->
