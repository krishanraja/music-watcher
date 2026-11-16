---
repo: krishanraja/music-watcher
product: music-watcher (trackcard and Krish's Music Brain)
as_of: 2026-11-16
head: 47a5d5d
lifecycle: building
production_url: none (runs on the worker server and on Krish's own machines)
state_doc: README.md
history_log: docs/history/now-notes/
truth_files: [docs/NORTH_STAR.md, taste/APPROVED.md]
authority_order: [docs/NORTH_STAR.md, AGENTS.md, README.md]
steward: https://github.com/krishanraja/ai-harness/blob/main/docs/steward/RUNBOOK.md
---

# music-watcher: where it is right now

## What it is

`trackcard` reads a WAV bounce locally and writes a plain-text card: tempo, key, a bar-numbered section map, which stems play in each section, the frequency balance, loudness, and a Splice brief of sounds that would fill measured gaps. `taste/` holds the Music Brain: what Krish likes, with its evidence. See `README.md`.

## Where it is right now (as of 2026-11-16)

<!-- north-star-state {"week_of":"2026-11-09","week_target":null,"current":null,"current_as_of":null,"current_source":null,"urgency":4,"urgency_reason":"North Star not set; Krish sets it"} --> **North Star number: U4, not measured.** The North Star is not set (`docs/NORTH_STAR.md`), so there is no number yet.

- A production engine, separate from the brains, is built and tested but not yet running: `trackcard engine plan|run|resume` (`engine/README.md`) reads Drive's Music Production folder, its Inspiration folder and the reasons sheet, decides from each bounce's name and upload date whether it is a new track or a new version (the real folder reads as Closure, 3 versions, plus two archived beats), measures it with trackcard, writes one brief per project for people, Claude and the coming Splice, Ableton and Suno MCPs, puts new sheet and drop words under the right voice in the shared evidence log, feeds each person's drops into their own brain's measured layer, and publishes one rolling PR behind a privacy gate that keeps Drive ids and emails out of this public repository; the README now lays out the whole project's parts, use cases and limits, and `docs/ROADMAP.md` proposes the next phases (my read, not yet set by Krish). (2026-11-16)
- The shared vocabulary has brass (sound_design) and build_into_drop (arrangement), and Krish's words on "Bird" and "Hey Sunshine" now count under them; "Hey Sunshine (Antonio Giacca Remix)" is measured with stems in `taste/cards/`, which shows its main build as a 28-bar breakdown carried by the vocal, with no low end for the last 16 bars and kick, bass and hats landing together on bar 141. (2026-11-15)
- Krish's evidence log holds his words on Time "Bird" (bass that punctuates, the brass motif, brass that sounds natural) and on Sugarstarr & Alexander "Hey Sunshine (Antonio Giacca Remix)" (the build before the drop, the vocals); organic sounds and percussive bass are now said across 2 tracks each, and brass and the build are filed as other/ words until the vocabulary grows. (2026-11-15)
- Calvin has a separate Music Brain in `taste/calvin/`: the graph of the 30-track "Fall Bangers" playlist (18 measured on the full track, each confirmed against Spotify's preview; 12 DRM-locked on SoundCloud), Calvin's own claims (3 proposed, waiting for Calvin) and `APPROVED.md`; every brain command takes `--taste taste/calvin`, and Krish's brain is unchanged. (2026-11-15)
- **It runs on the worker server** (Hetzner CPX32), installed for the service user on 14 Nov 2026. Its tests pass (85). A card with Demucs stem activity was written on CPU. `trackcard mcp` serves cards over stdio to a Claude session on the worker. (2026-11-14)
- **The Music Inspo watcher** (#2) runs every 15 minutes on the worker. Each new drop in Drive's Music Inspo becomes a card in `taste/inspo/` on one rolling pull request. The first drop was measured with stems in 5 min 25 s from a SoundCloud recording within 6 s of Spotify's length (#3, merged). (2026-11-14)
- **Admitted to the fleet** on Krish's ruling of 14 Nov (ai-harness `state/fleet.yaml`), on the same terms as claude-archive: the publisher does not write here. (2026-11-14)

## What changed recently

- 2026-11-15 2026-11-15: Calvin's Music Brain added (`taste/calvin/`); `build_graph.py` takes `--graph`, and a brain's `policy.json` can name its voices, its decider and a shared vocabulary and evidence log.
- 2026-11-14: joined the fleet: North Star stub, this file, the closeout fold.

## What is next and what is waiting on Krish

- Next (2026-11-16): on the worker, write `~/.music-watcher/engine.json`, run `trackcard engine plan` to confirm the worker's rclone sees the Music Production folder with owner metadata, then enable `music-engine.timer` and disable `music-inspo.timer` in the same step (`engine/README.md`, Worker setup).
- **Next:** decide how the content engine calls `trackcard` for audio treatment (an OS session proposes it; nothing calls it yet).
- **Waiting on Krish:** his North Star for this repository.
- North Star check (2026-11-16): holds.
