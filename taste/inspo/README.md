# Music Inspo (taste/inspo)

**Replaced by the production engine** (Krish's ruling, 2026-11-16): new drops go into Drive › Music Production ›
Inspiration and are measured by `trackcard engine run` (`engine/README.md`). The cards here stay; `watch.py` stops when
its timer is disabled on the worker.

What Krish drops into the Drive folder **Ventures › Inspiration › Music Inspo**, measured by trackcard, one card per
drop. Kept apart from `taste/graph/` on purpose: the graph is the Spotify playlist "Chillout & Ambient" and nothing
else. Same measurement, same evidence rules, so a drop can join the graph later if Krish says so.

| File | What it holds |
|---|---|
| `cards/<key>.trackcard.json` + `.md` | trackcard's full card (full track, Laplacian sections, Demucs stems unless they failed) |
| `index.csv` | one row per measured drop: title, artists, BPM, key, Camelot, loudness, drops, and where the audio came from |
| `fetch_log.jsonl` | every drop handled, including those **left for a home computer** or skipped, and why |

`key` is the Spotify track id when the drop was a Spotify link (the same id `taste/graph` uses), otherwise
`drive-<file id>` or `sc-<slug>`.

## How a drop is handled (`watch.py`)

- **Audio file** (wav, mp3, flac, m4a, aiff, ogg): measured as dropped.
- **Text file or Google Doc with a link:**
  - Spotify track: title, artists and length from the track page, then a SoundCloud recording whose real length is
    **within 6 s of Spotify's** (the graph's rule against wrong uploads). No match: left for a home computer.
  - SoundCloud: that recording.
  - YouTube: left for a home computer, because YouTube refuses datacenter machines.
- Audio is deleted once its card exists; it is never committed.

Only **new** drops are handled (Drive file id + checksum, kept in the worker's state file). A failed drop is retried
up to 3 times, then logged and given up.

## Where it runs

On Krish's worker server, every 15 minutes (`music-inspo.timer`), with read-only Drive access. It commits to the
rolling branch `inspo/new-drops` and keeps **one PR open** until Krish merges it; the next drop then starts a fresh
one. Settings (the Drive folder id, the checkout, tool paths) come from the worker's unit, not this repository.

Run one pass by hand on the worker: `sudo systemctl start music-inspo.service`, then
`journalctl -u music-inspo.service -n 30`.
