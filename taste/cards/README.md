# Cards for tracks pointed at in a session

Track cards for tracks Krish or Calvin pointed at in a session and asked to have measured: not Music Inspo drops (those are in
`taste/inspo/cards/`, written by the watcher) and not playlist tracks (those are in the graphs). Each card is trackcard's own
output, unedited. What was said about the track is in `taste/brain/evidence.jsonl`; a card is measurement, never evidence.

| card | track | asked by | audio | measured |
|---|---|---|---|---|
| `4rKhvvWaSNlUCJFdJDTDFK` | Sugarstarr, Alexander, Antonio Giacca - Hey Sunshine (Antonio Giacca Remix), https://open.spotify.com/track/4rKhvvWaSNlUCJFdJDTDFK | Krish, 2026-11-15, for the build before the drop | SoundCloud upload by Happy Music (https://soundcloud.com/happymusic/sugarstarr-feat-alexander-hey-sunshine-antonio-giacca-remix), 403.5 s against Spotify's 403 s; Spotify's 30 s preview found in it (match 0.993) | `trackcard analyze --json --sections laplacian`, with Demucs stems, on the worker |

## Hey Sunshine: the build Krish likes

Krish's words (evidence row `hey-sunshine-krish`): "I love the way this builds before the drop, and the vocals".

Measured (bar numbers from the card; 122 BPM, so a bar is about 2 s):

- **Three drops**: 1:35 (bar 49), 2:53 (bar 89) and the main drop at 4:36 (bar 141). The breakdowns before them run
  16 bars, then 8, then 28 bars before the main drop.
- **The main run-up, 3:41-4:36 (bars 113-140).** The kick pulls back at bar 112 and the bassline drops out at bar 114; the sub
  band falls to 29 dB below the loudest band, and the section sits about 4 dB below the drops. The vocal-range layer comes in
  fuller at bar 118. The hats drop out at bar 122. The chords swell (+8 dB) at bar 125, where trackcard marks the run-up's
  start: 16 bars with no low end. The hats come back at bar 132, 9 bars before the drop, ease off at bar 136, and the vocal
  swells again at bar 139.
- **The landing.** At bar 141 the kick (+16 dB), the bassline and the hats (+24 dB) arrive on the same bar. The vocal steps out
  at bar 142 and returns with the chords 15-16 bars into the drop (bars 156-157).
- **The vocals live in the breakdowns.** The vocal stem sounds in 84-97% of each breakdown and in only 14-30% of each peak
  section. (On any track, the vocal stem can also pick up vocal-like synths.)
- Elsewhere: A# minor or A# major (trackcard is unsure between the two), 6:43, and a loud master: -6.3 LUFS with an 8.9 dB
  crest, louder than any playlist median in the graphs.

My read: the build works by taking the low end away for a long stretch and handing the track to the vocal, then stripping
the hats, lifting the chords, and bringing the hats back 9 bars out, so that kick, bass and hats hit together. The vocal
carries the tension and steps aside for the drop.

The card's Splice brief (section 6) is written for a producer's own bounce; on a finished record its "gaps" are the
arrangement's choices, not missing parts.
