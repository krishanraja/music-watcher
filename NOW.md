---
repo: krishanraja/music-watcher
product: music-watcher (trackcard and Krish's Music Brain)
as_of: 2026-11-14
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

## Where it is right now (as of 2026-11-14)

<!-- north-star-state {"week_of":"2026-11-09","week_target":null,"current":null,"current_as_of":null,"current_source":null,"urgency":4,"urgency_reason":"North Star not set; Krish sets it"} --> **North Star number: U4, not measured.** The North Star is not set (`docs/NORTH_STAR.md`), so there is no number yet.

- **It runs on the worker server** (Hetzner CPX32), installed for the service user on 14 Nov 2026. Its tests pass (85). A card with Demucs stem activity was written on CPU. `trackcard mcp` serves cards over stdio to a Claude session on the worker. (2026-11-14)
- **The Music Inspo watcher** (#2) runs every 15 minutes on the worker. Each new drop in Drive's Music Inspo becomes a card in `taste/inspo/` on one rolling pull request. The first drop was measured with stems in 5 min 25 s from a SoundCloud recording within 6 s of Spotify's length (#3, merged). (2026-11-14)
- **Admitted to the fleet** on Krish's ruling of 14 Nov (ai-harness `state/fleet.yaml`), on the same terms as claude-archive: the publisher does not write here. (2026-11-14)

## What changed recently

- 2026-11-14: joined the fleet: North Star stub, this file, the closeout fold.

## What is next and what is waiting on Krish

- **Next:** decide how the content engine calls `trackcard` for audio treatment (an OS session proposes it; nothing calls it yet).
- **Waiting on Krish:** his North Star for this repository.
