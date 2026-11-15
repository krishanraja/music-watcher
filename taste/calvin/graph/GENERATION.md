# Generating from Calvin's taste graph

Read this before writing, arranging or choosing sounds for a track that should sound like Calvin's taste. Rules Calvin has
approved are in `taste/calvin/APPROVED.md` and win over anything here; the numbers below are evidence, not rules. For Krish's
taste, read `taste/graph/GENERATION.md` instead: the two brains are kept apart on purpose.

The graph (`graph.json`, `tracks.csv`) holds all 30 tracks of Calvin's Spotify playlist "Fall Bangers"
(https://open.spotify.com/playlist/1inChKFsQRxfnGMBagrEib, read 2026-11-15 from Spotify's public pages, no login), linked to
their artists, labels, release years, keys, tempo bands, measured traits, inferred style families and `sounds_like` edges
between the nearest tracks.

**Where each number comes from.** Titles, artists, lengths, release dates and added dates: Spotify's public pages (details in
`playlist.json`). Labels: the ℗ line on each album page, 30 of 30. Measured by trackcard on the **full track** for 18 of 30
tracks (no stems, Laplacian sections). The audio came from SoundCloud, accepted only when the file's real length was within
6 s of Spotify's, and every accepted file was checked for the right recording by finding Spotify's own 30 s preview inside it
(waveform match 0.90 to 0.99 for the 18 accepted; 0.01 to 0.19 for the wrong uploads it turned down, one of them only 0.4 s off
Spotify's length). Each track's `audio_source` and `measured_from` say where its audio came from. No preview clips are measured.
12 tracks have no audio yet (below). No stems, so there are no drop counts or vocal readings. Style families are Claude's read
of the artists (`families.json`), not measured.

Rebuild: `python taste/graph/build_graph.py <folder of <spotify id>.trackcard.json + fetch_log.jsonl> --graph taste/calvin/graph`,
then `trackcard brain render --taste taste/calvin`. There is no chronology: Calvin added all 30 tracks in one evening
(14-15 Nov 2026), so the adding order says nothing about how the taste moved.

## The target, in numbers (medians over 18 full tracks, middle half in brackets), next to Krish's

| what | Calvin | Krish (342 tracks) | use it as |
|---|---|---|---|
| tempo | 130 BPM (126-132); 14 of 18 at 126 or faster | 122 BPM (118-125) | default 128-130; 125 for the disco side |
| mode | 11 minor, 7 major | 192 minor, 150 major | minor a little more often, as with Krish |
| keys | spread over 15 keys; only A minor (8A), F# minor (11A) and E-flat major (5B) appear twice | G minor, F minor, A minor lead | no home key: take the key from the idea |
| loudness | -8.6 LUFS (-9.3 to -7.6) | -9.9 LUFS | master to about -8.5: louder than Krish's target |
| dynamics | crest 10.5 dB (9.9-11.3) | 11.7 dB | punchier and denser, but not crushed (only 1 track under 8.5 dB) |
| tonal balance | low band loudest in 11 of 18; sub -4, mid -4, high-mid -10, air -16 dB | sub -7, high-mid -13, air -20 dB | more sub and much more top: bright hats and shakers are welcome here |
| length | 3:16 over all 30 tracks (2:55-3:51); 3 of 30 run 6 minutes or more | 4:33 | radio edits: 3-4 minutes |
| era | 25 of 30 released in 2026 | released 2014 | current club records, mostly this year's |

**Arrangement (18 full tracks).** About 7 sections. The first full-energy section arrives after a median of 8 bars (15 s),
and 16 of 18 tracks reach full energy within 16 bars. They sit at full energy for about 68% of their length, with 2 breakdowns.
My read: these are DJ-ready radio edits that drop you straight into the groove, shorter and harder than Krish's picks, with the
same habit of getting to the groove quickly. Arrangement figures come from the full mix without stems.

## The families (inferred), with measured settings

Two of Calvin's families are Krish's (same name and definition in both graphs); two are new. Share is of all 30 tracks, by the
first credited artist's family.

| family | tracks (measured) | tempo (range) | mode | sound | arrangement |
|---|---|---|---|---|---|
| Groove-led tech house (Cloonee, Chris Lorenzo, ANOTR, TYGE, Toman, Riordan) | 15 (8) | 130 (126-132) | 4 minor : 4 major | densest (crest 10.1), air -16.2 | 8-bar intro, 70% at full energy, 2 breakdowns, 3:13 |
| UK and soulful vocal house (Claptone, LP Giobbi, KETTAMA, Dam Swindle) | 7 (5) | 129 (125-135) | 4 minor : 1 major | most dynamic (crest 11.2), -9.4 LUFS | 8-bar intro, 70% at full energy, 2 breakdowns |
| Disco, French touch and indie dance (The Paradise, Roog, Edd, CŒUR ACIDE), new | 6 (4) | 122.5 (103-132) | 2 : 2 | brightest (air -14.5) | 12-bar intro, 58% at full energy |
| Afro and Latin club house (Francis Mercier, unfazed), new | 2 (1) | 126 | 1 minor | air -16 | 8-bar intro, 55% at full energy |

Calvin's playlist is half groove-led tech house (15 of 30); in Krish's graph that family holds 12 of 346. Krish's groove-led
tech house runs slower and darker (125 BPM, air -18.2 dB over 11 tracks) than Calvin's (130 BPM, air -16.2).

## Where the two brains meet

- One track is in both playlists: Toman, "Verano En NY" (Solid Grooves). It measured the same in both graphs (126 BPM, G minor,
  -8.7 LUFS, air -17.6 dB).
- Four artists are in both: Claptone, Barry Can't Swim and Dam Swindle (UK and soulful vocal house in both graphs) and Toman.
- My read: for a track the two of them make together, the overlap is groove-led and soulful house at 125-126 BPM, getting to
  the groove by bar 8. Calvin pulls it faster, louder and brighter; Krish pulls it slower, warmer and softer on top.

## Prompting a generator or picking sounds for Calvin

1. Read `taste/calvin/APPROVED.md` first; follow only what is accepted there.
2. Pick the family, then take its row above as the defaults (BPM, mode, how bright).
3. Pick 2-3 reference tracks from that family in `tracks.csv` and follow their `sounds_like` edges in `graph.json`.
4. Keys: stay in the chosen key or a Camelot neighbour (`mixes_with` edges).
5. Arrangement: full energy by bar 8, about 70% of the track at full energy, 2 breakdowns, 3-4 minutes.
6. Mix: about -8.5 LUFS with a 10-11 dB crest, strong sub and low end, and a bright, open top.

## Still to measure

- 12 tracks have no audio (`measured_from` = none in `tracks.csv`), left for a home computer, where content-watcher's YouTube
  route works. On SoundCloud each one's official upload is DRM-protected and no other upload carried Spotify's recording:
  KDAY "As You Are"; Marco Lys, Michael Ekow, Kevcody "Super Hot"; The Martinez Brothers, Stevie Appleton "Impressions";
  Jazzy, Chris Lorenzo "Invisible"; Collect 200 "Everything Will Be Alright"; veggi, Barney Bones "SHAKE SUM"; Wal "What Ya
  Got"; Sam Gellaitry "START UP A RUMOUR"; LOVE LANGUAGE et al. "PARTYS OVER (James Juke Remix)"; Julien Jabre, Purple Disco
  Machine "Swimming Places (Purple Disco Machine Re-Work)" (no upload within 6 s at all); unfazed et al. "A Gira (Remix)";
  Barry Can't Swim "Dance Dance Dance!". Seven of the 12 are groove-led tech house, so the tech-house figures above are the
  thinnest.
- Stems: run `trackcard analyze <wav> --json --sections laplacian` (with stems) to add drops, stem densities and a vocal
  reading. These are short tracks: my estimate from the worker's 3 to 4.5 minutes per 4-5 minute track is 2 to 3 minutes each.
