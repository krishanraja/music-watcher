# Track card: 4rKhvvWaSNlUCJFdJDTDFK.wav

Analysed 2026-11-15 14:18 by trackcard 0.4.0, locally from the audio file. 44100 Hz, 2 ch.

**How to read this card (for an AI with no other context):** trackcard listened to an unreleased WAV bounce and measured it. Bar numbers count from bar 1 at the first downbeat, 4/4 assumed, so the producer can point at a moment ("bar 33") and you can find it in the section map. Stem states come from AI source separation (Demucs): *active* = sounding in most of the section, *sparse* = sounding some of the time, *absent* = essentially silent. Everything here is measured, not heard; where a method fell back or is uncertain, it says so below. The Splice brief (section 6) lists sound requests you can act on directly.

**Read this first (fallbacks and caveats):**
- Beat grid moved by half a beat: the tracker had locked onto the off-beat (the kick/bass band hits half a beat later).
- No GPU found; Demucs ran on CPU.
- 52272 samples hit 0 dBFS; the bounce may be clipping.

## 1. Basics

- Duration: 6:43 (403.5 s)
- BPM: 122 measured, likely project tempo **122**. Confidence high: one steady tempo fits the whole track (grid score 2.2x the typical neighbouring tempo), as in a DAW bounce.
- Time signature: 4/4 (assumed)
- Bar grid: beat 1 chosen from kick/bass (<250 Hz) onset strength (bounce does not start on a beat)
- Key: **A# minor**, Camelot **3A**. Confidence medium (runner-up A# major, margin 0.030).
- Also likely: **A# major (6B)**: the two keys score within 0.03 of each other. Ask the producer which one is home before filtering by key.
- Harmonically compatible keys: F minor (4A), D# minor (2A), C# major (3B)

## 2. Section map

Method: librosa Laplacian segmentation (FALLBACK: labels are section_N, same N = similar material; they are not intro/verse/drop names). 2 boundaries were moved by one bar onto a 4-bar phrase start (bars 1, 5, 9, ...).

| # | label | bars | time | length | energy |
|---|---|---|---|---|---|
| S1 | section_1 | 0-32 (33 bars) | 0:00-1:03 | 63 s | peak (-1.9 dB) |
| S2 | section_2 | 33-48 (16 bars) | 1:03-1:35 | 31 s | mid (-4.2 dB) |
| S3 | section_1 | 49-80 (32 bars) | 1:35-2:38 | 63 s | peak (+0.0 dB) |
| S4 | section_2 | 81-88 (8 bars) | 2:38-2:53 | 16 s | mid (-5.7 dB) |
| S5 | section_1 | 89-112 (24 bars) | 2:53-3:41 | 47 s | peak (-0.1 dB) |
| S6 | section_2 | 113-140 (28 bars) | 3:41-4:36 | 55 s | mid (-4.1 dB) |
| S7 | section_1 | 141-188 (48 bars) | 4:36-6:10 | 94 s | peak (-0.4 dB) |
| S8 | section_2 | 189-196 (8 bars) | 6:10-6:26 | 16 s | mid (-7.1 dB) |
| S9 | section_3 | 197-205 (9 bars) | 6:26-6:43 | 18 s | low (-26.9 dB) |

Energy is the section's RMS level against the loudest section: peak (within 3 dB), mid (3-8 dB down), low (more than 8 dB down). The loudest sections are the likely drops or peaks.

### Drops and layer changes

- Drop, 1:35, bar 49. Run-up: low end cut from 1:03 (bar 33, 16 bars). Drop: staged: kick and low drums first, then bassline at bar 50; hats and cymbals (drum tops) at bar 50; vocal-range layer (vocals or a lead) at bar 61; synths/chords layer at bar 63.
- Drop, 2:53, bar 89. Run-up: build from 2:28 (bar 76: vocal-range layer (vocals or a lead) drops out); low end cut from 2:36 (bar 80, 9 bars). Drop: staged: kick and low drums first, then bassline at bar 89; vocal-range layer (vocals or a lead) at bar 93; synths/chords layer at bar 95; vocal-range layer (vocals or a lead) at bar 97; vocal-range layer (vocals or a lead) at bar 104.
- **Main drop**, 4:36, bar 141. Run-up: low end cut from 4:04 (bar 125, 16 bars). Drop: staged: kick and low drums first, then bassline at bar 141; synths/chords layer at bar 156; vocal-range layer (vocals or a lead) at bar 157.

A drop is bass or kick jumping to full level after at least 4 bars well below it; layers that rise within the next 16 bars join it. The run-up is the build (earliest layer change in the 16 bars before) and the cut (where the low end went out). The main drop is the last drop with a run-up before the final 15% of the track: an arrangement convention, since staged drops are often mixed to the same level.

Every layer change, by bar (kick = drums below 150 Hz, tops = drums above 5 kHz):

- 0:14 bar 8: vocal-range layer (vocals or a lead) pulls back (-13 dB)
- 0:20 bar 11: vocal-range layer (vocals or a lead) comes in fuller (+9 dB)
- 0:26 bar 14: vocal-range layer (vocals or a lead) drops out; synths/chords layer comes in fuller (+6 dB)
- 0:34 bar 18: vocal-range layer (vocals or a lead) drops out
- 0:38 bar 20: synths/chords layer comes in fuller (+10 dB)
- 0:43 bar 23: synths/chords layer comes in fuller (+6 dB)
- 1:01 bar 32: vocal-range layer (vocals or a lead) comes in fuller (+27 dB)
- 1:05 bar 34: kick and low drums pull back (-14 dB)
- 1:13 bar 38: vocal-range layer (vocals or a lead) comes in fuller (+15 dB)
- 1:29 bar 46: kick and low drums pull back (-21 dB); hats and cymbals (drum tops) pull back (-9 dB)
- 1:35 bar 49: DROP: kick and low drums come in fuller (+27 dB); vocal-range layer (vocals or a lead) pulls back (-8 dB)
- 1:37 bar 50: bassline enters, joining the drop at bar 50; hats and cymbals (drum tops) come in fuller (+16 dB), joining the drop at bar 49
- 1:41 bar 52: vocal-range layer (vocals or a lead) pulls back (-22 dB)
- 1:46 bar 55: vocal-range layer (vocals or a lead) drops out
- 1:58 bar 61: vocal-range layer (vocals or a lead) enters, joining the drop at bar 49
- 2:02 bar 63: synths/chords layer comes in fuller (+18 dB), joining the drop at bar 49
- 2:06 bar 65: vocal-range layer (vocals or a lead) drops out
- 2:20 bar 72: vocal-range layer (vocals or a lead) enters
- 2:28 bar 76: vocal-range layer (vocals or a lead) drops out
- 2:36 bar 80: kick and low drums pull back (-18 dB); vocal-range layer (vocals or a lead) comes in fuller (+29 dB)
- 2:40 bar 82: bassline drops out
- 2:43 bar 84: hats and cymbals (drum tops) pull back (-18 dB)
- 2:45 bar 85: vocal-range layer (vocals or a lead) comes in fuller (+10 dB)
- 2:53 bar 89: DROP: kick and low drums come in fuller (+17 dB); bassline enters, joining the drop at bar 89; hats and cymbals (drum tops) come in fuller (+26 dB); vocal-range layer (vocals or a lead) drops out
- 3:01 bar 93: vocal-range layer (vocals or a lead) enters, joining the drop at bar 89
- 3:05 bar 95: vocal-range layer (vocals or a lead) drops out; synths/chords layer comes in fuller (+8 dB), joining the drop at bar 89
- 3:09 bar 97: vocal-range layer (vocals or a lead) comes in fuller (+8 dB), joining the drop at bar 89
- 3:11 bar 98: synths/chords layer pulls back (-10 dB)
- 3:15 bar 100: vocal-range layer (vocals or a lead) drops out
- 3:23 bar 104: vocal-range layer (vocals or a lead) enters, joining the drop at bar 89
- 3:33 bar 109: vocal-range layer (vocals or a lead) pulls back (-33 dB)
- 3:37 bar 111: vocal-range layer (vocals or a lead) comes in fuller (+20 dB)
- 3:39 bar 112: kick and low drums pull back (-18 dB)
- 3:42 bar 114: bassline drops out; vocal-range layer (vocals or a lead) pulls back (-15 dB)
- 3:50 bar 118: vocal-range layer (vocals or a lead) comes in fuller (+20 dB); synths/chords layer pulls back (-13 dB)
- 3:52 bar 119: hats and cymbals (drum tops) pull back (-15 dB)
- 3:58 bar 122: hats and cymbals (drum tops) drop out
- 4:04 bar 125: synths/chords layer comes in fuller (+8 dB)
- 4:18 bar 132: hats and cymbals (drum tops) enter
- 4:22 bar 134: vocal-range layer (vocals or a lead) pulls back (-14 dB)
- 4:26 bar 136: hats and cymbals (drum tops) pull back (-7 dB)
- 4:32 bar 139: vocal-range layer (vocals or a lead) comes in fuller (+6 dB)
- 4:36 bar 141: DROP: kick and low drums come in fuller (+16 dB); bassline enters, joining the drop at bar 141; hats and cymbals (drum tops) come in fuller (+24 dB)
- 4:38 bar 142: vocal-range layer (vocals or a lead) drops out
- 4:42 bar 144: synths/chords layer pulls back (-6 dB)
- 4:53 bar 150: synths/chords layer pulls back (-10 dB)
- 5:05 bar 156: synths/chords layer comes in fuller (+8 dB), joining the drop at bar 141
- 5:07 bar 157: vocal-range layer (vocals or a lead) comes in fuller (+34 dB), joining the drop at bar 141
- 5:15 bar 161: vocal-range layer (vocals or a lead) drops out
- 5:19 bar 163: synths/chords layer comes in fuller (+7 dB)
- 5:21 bar 164: vocal-range layer (vocals or a lead) comes in fuller (+14 dB)
- 5:27 bar 167: vocal-range layer (vocals or a lead) pulls back (-16 dB); synths/chords layer pulls back (-18 dB)
- 5:35 bar 171: vocal-range layer (vocals or a lead) pulls back (-14 dB)
- 5:37 bar 172: synths/chords layer comes in fuller (+13 dB)
- 5:50 bar 179: vocal-range layer (vocals or a lead) pulls back (-9 dB)
- 5:54 bar 181: bassline drops out; synths/chords layer pulls back (-15 dB)
- 5:56 bar 182: vocal-range layer (vocals or a lead) drops out
- 6:12 bar 190: kick and low drums pull back (-19 dB)
- 6:24 bar 196: synths/chords layer comes in fuller (+23 dB)
- 6:28 bar 198: kick and low drums drop out; hats and cymbals (drum tops) drop out; vocal-range layer (vocals or a lead) enters
- 6:32 bar 200: synths/chords layer drops out
- 6:42 bar 205: hats and cymbals (drum tops) drop out; vocal-range layer (vocals or a lead) drops out

## 3. Stem activity

Demucs htdemucs on cpu (shifts=0), 10 Hz RMS envelopes. Cell = state and % of 100 ms frames where the stem sounds. 'other' holds everything that is not drums, bass or vocals (synths, chords, pads, leads, fx). On instrumental tracks the vocals stem can pick up vocal-like synths or leads.

| # | bars | drums | bass | vocals | other |
|---|---|---|---|---|---|
| S1 | 0-32 | active 100% | absent | sparse 14% | active 57% |
| S2 | 33-48 | active 86% | absent | active 96% | active 97% |
| S3 | 49-80 | active 100% | active 68% | sparse 30% | active 79% |
| S4 | 81-88 | active 72% | absent | active 84% | active 100% |
| S5 | 89-112 | active 100% | active 69% | sparse 24% | active 82% |
| S6 | 113-140 | active 61% | absent | active 97% | active 99% |
| S7 | 141-188 | active 100% | active 57% | sparse 19% | active 60% |
| S8 | 189-196 | active 100% | absent | absent | sparse 16% |
| S9 | 197-205 | absent | absent | absent | sparse 28% |

## 4. Frequency balance per section

dB relative to the loudest band in that section (0 = loudest). Bands: sub 20-60 Hz, low 60-250 Hz, mid 250 Hz-2 kHz, high-mid 2-8 kHz, air 8-20 kHz.

| # | bars | sub | low | mid | high-mid | air | flags |
|---|---|---|---|---|---|---|---|
| S1 | 0-32 | -3 | 0 | -7 | -9 | -9 | balanced |
| S2 | 33-48 | -29 | -8 | 0 | -8 | -13 | light on sub |
| S3 | 49-80 | -1 | 0 | -6 | -9 | -10 | balanced |
| S4 | 81-88 | -27 | -6 | 0 | -8 | -18 | light on sub |
| S5 | 89-112 | -1 | 0 | -6 | -9 | -10 | balanced |
| S6 | 113-140 | -29 | -7 | 0 | -10 | -20 | light on sub |
| S7 | 141-188 | -1 | 0 | -6 | -9 | -10 | balanced |
| S8 | 189-196 | -24 | -3 | -0 | 0 | -1 | balanced |
| S9 | 197-205 | -27 | -16 | 0 | -0 | -30 | light on sub; thin low end (60-250 Hz) |

## 5. Loudness and dynamics

- Whole track: peak 0.0 dBFS, RMS -8.9 dBFS, -6.3 LUFS integrated (ITU-R BS.1770 via pyloudnorm), crest factor 8.9 dB.
- 52272 samples at 0 dBFS (possible clipping).
- Per section (RMS dBFS, change from the previous section):
  - S1 bars 0-32: -9.2
  - S2 bars 33-48: -11.5 (-2.3 dB)
  - S3 bars 49-80: -7.3 (+4.2 dB)
  - S4 bars 81-88: -13.0 (-5.7 dB)
  - S5 bars 89-112: -7.4 (+5.6 dB)
  - S6 bars 113-140: -11.4 (-4.0 dB)
  - S7 bars 141-188: -7.7 (+3.7 dB)
  - S8 bars 189-196: -14.4 (-6.7 dB)
  - S9 bars 197-205: -34.2 (-19.8 dB)
- Every 8 bars (RMS dBFS): 1-8: -9 | 9-16: -10 | 17-24: -9 | 25-32: -9 | 33-40: -12 | 41-48: -11 | 49-56: -7 | 57-64: -7 | 65-72: -7 | 73-80: -8 | 81-88: -13 | 89-96: -7 | 97-104: -7 | 105-112: -8 | 113-120: -12 | 121-128: -10 | 129-136: -11 | 137-144: -9 | 145-152: -7 | 153-160: -7 | 161-168: -8 | 169-176: -8 | 177-184: -8 | 185-192: -11 | 193-200: -17 | 201-205: -44

## 6. Splice brief

Track facts for every search: **122 BPM**, **A# minor (3A)** or **A# major (6B)** (unconfirmed). Each row is a gap trackcard measured, with the evidence. Use the BPM range and key as Splice filters, the layer as the instrument type, and try the candidate tags in order. Ask the producer before replacing anything that is already there.

### 1. S1, bars 0-32: bass
- Gap: no bassline in a peak-energy section
- Evidence: bass stem absent; section level -1.9 dB vs the loudest section
- BPM range: 120-124
- Key: A# minor (3A) or A# major (6B); trackcard is unsure between the two, so confirm with the producer; also works: F minor (4A), D# minor (2A), C# major (3B)
- Layer type: bass
- Candidate Splice tags: basslines, bass loops, sub bass, synth bass
- Do this: Search Splice for bass loops at 120-124 BPM, key A# minor (or A# major), tags: basslines, bass loops, sub bass. Use it in bars 0-32 to anchor the low end.

### 2. S2, S4, bars 33-48, 81-88: fx
- Gap: nothing builds into the next section
- Evidence: next section is 4.2 dB louder
- BPM range: 120-124
- Key: any (unpitched; skip the key filter)
- Layer type: fx
- Candidate Splice tags: risers, uplifters, sweeps, white noise, fx
- Do this: Search Splice for fx samples at 120-124 BPM, tags: risers, uplifters, sweeps. Use it in bars 33-48, 81-88 to build into the next section (last 4-8 bars).

### 3. S8, bars 189-196: pads
- Gap: little harmonic content
- Evidence: 'other' stem (chords/pads/synths) sparse and vocals stem absent
- BPM range: 120-124
- Key: A# minor (3A) or A# major (6B); trackcard is unsure between the two, so confirm with the producer; also works: F minor (4A), D# minor (2A), C# major (3B)
- Layer type: pads
- Candidate Splice tags: pads, atmospheres, textures, drones
- Do this: Search Splice for pads samples at 120-124 BPM, key A# minor (or A# major), tags: pads, atmospheres, textures. Use it in bars 189-196 to add harmony in the mids.

### 4. S8, bars 189-196: pads
- Gap: low-energy section is very bare
- Evidence: 1 stem(s) active; section level -7.1 dB vs the loudest section
- BPM range: 120-124
- Key: A# minor (3A) or A# major (6B); trackcard is unsure between the two, so confirm with the producer; also works: F minor (4A), D# minor (2A), C# major (3B)
- Layer type: pads
- Candidate Splice tags: pads, atmospheres, textures, drones
- Do this: Search Splice for pads samples at 120-124 BPM, key A# minor (or A# major), tags: pads, atmospheres, textures. Use it in bars 189-196 to add texture without adding energy.

### 5. S9, bars 197-205: pads
- Gap: little harmonic content
- Evidence: 'other' stem (chords/pads/synths) sparse and vocals stem absent
- BPM range: 120-124
- Key: A# minor (3A) or A# major (6B); trackcard is unsure between the two, so confirm with the producer; also works: F minor (4A), D# minor (2A), C# major (3B)
- Layer type: pads
- Candidate Splice tags: pads, atmospheres, textures, drones
- Do this: Search Splice for pads samples at 120-124 BPM, key A# minor (or A# major), tags: pads, atmospheres, textures. Use it in bars 197-205 to add harmony in the mids.

### 6. S9, bars 197-205: pads
- Gap: low-energy section is very bare
- Evidence: 0 stem(s) active; section level -26.9 dB vs the loudest section
- BPM range: 120-124
- Key: A# minor (3A) or A# major (6B); trackcard is unsure between the two, so confirm with the producer; also works: F minor (4A), D# minor (2A), C# major (3B)
- Layer type: pads
- Candidate Splice tags: pads, atmospheres, textures, drones
- Do this: Search Splice for pads samples at 120-124 BPM, key A# minor (or A# major), tags: pads, atmospheres, textures. Use it in bars 197-205 to add texture without adding energy.
