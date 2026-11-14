# Track card: 7DxrTNmUprBMQ0RV45xreb.wav

Analysed 2026-11-14 21:36 by trackcard 0.4.0, locally from the audio file. 44100 Hz, 2 ch.

**How to read this card (for an AI with no other context):** trackcard listened to an unreleased WAV bounce and measured it. Bar numbers count from bar 1 at the first downbeat, 4/4 assumed, so the producer can point at a moment ("bar 33") and you can find it in the section map. Stem states come from AI source separation (Demucs): *active* = sounding in most of the section, *sparse* = sounding some of the time, *absent* = essentially silent. Everything here is measured, not heard; where a method fell back or is uncertain, it says so below. The Splice brief (section 6) lists sound requests you can act on directly.

**Read this first (fallbacks and caveats):**
- Beat grid moved by half a beat: the tracker had locked onto the off-beat (the kick/bass band hits half a beat later).
- No GPU found; Demucs ran on CPU.
- 113 samples hit 0 dBFS; the bounce may be clipping.

## 1. Basics

- Duration: 4:06 (246.0 s)
- BPM: 126 measured, likely project tempo **126**. Confidence high: one steady tempo fits the whole track (grid score 2.1x the typical neighbouring tempo), as in a DAW bounce.
- Time signature: 4/4 (assumed)
- Bar grid: beat 1 chosen from kick/bass (<250 Hz) onset strength (bounce does not start on a beat)
- Key: **G minor**, Camelot **6A**. Confidence medium (runner-up G major, margin 0.133).
- Also likely: **D# major (5B)**: they share 6 of 7 notes and a second key profile (Temperley) ranks D# major close behind. Ask the producer which one is home before filtering by key.
- Harmonically compatible keys: D minor (7A), C minor (5A), A# major (6B)

## 2. Section map

Method: librosa Laplacian segmentation (FALLBACK: labels are section_N, same N = similar material; they are not intro/verse/drop names). 2 boundaries were moved by one bar onto a 4-bar phrase start (bars 1, 5, 9, ...).

| # | label | bars | time | length | energy |
|---|---|---|---|---|---|
| S1 | section_1 | 0-8 (9 bars) | 0:00-0:15 | 15 s | peak (-2.1 dB) |
| S2 | section_2 | 9-40 (32 bars) | 0:15-1:16 | 61 s | peak (+0.0 dB) |
| S3 | section_3 | 41-48 (8 bars) | 1:16-1:32 | 15 s | low (-8.3 dB) |
| S4 | section_4 | 49-56 (8 bars) | 1:32-1:47 | 15 s | mid (-6.2 dB) |
| S5 | section_2 | 57-120 (64 bars) | 1:47-3:49 | 122 s | peak (-0.2 dB) |
| S6 | section_1 | 121-130 (10 bars) | 3:49-4:06 | 17 s | peak (-0.8 dB) |

Energy is the section's RMS level against the loudest section: peak (within 3 dB), mid (3-8 dB down), low (more than 8 dB down). The loudest sections are the likely drops or peaks.

### Drops and layer changes

- Drop, 0:17, bar 10. Run-up: build from 0:12 (bar 7: kick and low drums drop out). Drop: staged: kick and low drums first, then bassline at bar 10; vocal-range layer (vocals or a lead) at bar 24.
- **Main drop**, 1:49, bar 58. Run-up: low end cut from 1:18 (bar 42, 16 bars). Drop: staged: kick and low drums first, then synths/chords layer at bar 72.

A drop is bass or kick jumping to full level after at least 4 bars well below it; layers that rise within the next 16 bars join it. The run-up is the build (earliest layer change in the 16 bars before) and the cut (where the low end went out). The main drop is the last drop with a run-up before the final 15% of the track: an arrangement convention, since staged drops are often mixed to the same level.

Every layer change, by bar (kick = drums below 150 Hz, tops = drums above 5 kHz):

- 0:12 bar 7: kick and low drums drop out
- 0:17 bar 10: DROP: kick and low drums come in fuller (+23 dB); bassline enters, joining the drop at bar 10
- 0:44 bar 24: vocal-range layer (vocals or a lead) enters, joining the drop at bar 10
- 0:48 bar 26: vocal-range layer (vocals or a lead) drops out
- 1:18 bar 42: kick and low drums drop out; hats and cymbals (drum tops) pull back (-8 dB)
- 1:34 bar 50: kick and low drums enter; synths/chords layer comes in fuller (+15 dB)
- 1:45 bar 56: hats and cymbals (drum tops) pull back (-16 dB)
- 1:47 bar 57: vocal-range layer (vocals or a lead) enters
- 1:49 bar 58: DROP: kick and low drums come in fuller (+32 dB); bassline comes in fuller (+6 dB); hats and cymbals (drum tops) come in fuller (+20 dB); synths/chords layer pulls back (-12 dB)
- 2:15 bar 72: kick and low drums pull back (-23 dB); synths/chords layer comes in fuller (+7 dB), joining the drop at bar 58
- 2:17 bar 73: vocal-range layer (vocals or a lead) drops out
- 2:35 bar 82: synths/chords layer comes in fuller (+12 dB)
- 2:48 bar 89: vocal-range layer (vocals or a lead) enters
- 2:50 bar 90: synths/chords layer pulls back (-9 dB)
- 2:52 bar 91: vocal-range layer (vocals or a lead) drops out
- 3:07 bar 99: vocal-range layer (vocals or a lead) enters
- 3:15 bar 103: vocal-range layer (vocals or a lead) drops out
- 3:16 bar 104: synths/chords layer comes in fuller (+7 dB)
- 3:53 bar 123: bassline drops out
- 4:04 bar 129: synths/chords layer drops out

## 3. Stem activity

Demucs htdemucs on cpu (shifts=0), 10 Hz RMS envelopes. Cell = state and % of 100 ms frames where the stem sounds. 'other' holds everything that is not drums, bass or vocals (synths, chords, pads, leads, fx). On instrumental tracks the vocals stem can pick up vocal-like synths or leads.

| # | bars | drums | bass | vocals | other |
|---|---|---|---|---|---|
| S1 | 0-8 | active 94% | absent | absent | active 97% |
| S2 | 9-40 | active 99% | active 99% | absent | active 100% |
| S3 | 41-48 | active 81% | active 95% | absent | active 100% |
| S4 | 49-56 | active 84% | active 99% | absent | active 100% |
| S5 | 57-120 | active 97% | active 93% | sparse 17% | active 99% |
| S6 | 121-130 | active 99% | sparse 12% | absent | active 76% |

## 4. Frequency balance per section

dB relative to the loudest band in that section (0 = loudest). Bands: sub 20-60 Hz, low 60-250 Hz, mid 250 Hz-2 kHz, high-mid 2-8 kHz, air 8-20 kHz.

| # | bars | sub | low | mid | high-mid | air | flags |
|---|---|---|---|---|---|---|---|
| S1 | 0-8 | 0 | -3 | -10 | -16 | -23 | sub-heavy: sub sits 3 dB over the low band |
| S2 | 9-40 | 0 | -2 | -10 | -14 | -18 | balanced |
| S3 | 41-48 | -7 | 0 | -6 | -12 | -21 | balanced |
| S4 | 49-56 | -22 | 0 | -1 | -6 | -19 | balanced |
| S5 | 57-120 | 0 | -2 | -8 | -12 | -16 | balanced |
| S6 | 121-130 | 0 | -3 | -11 | -14 | -18 | sub-heavy: sub sits 3 dB over the low band |

## 5. Loudness and dynamics

- Whole track: peak 0.0 dBFS, RMS -9.6 dBFS, -8.7 LUFS integrated (ITU-R BS.1770 via pyloudnorm), crest factor 9.6 dB.
- 113 samples at 0 dBFS (possible clipping).
- Per section (RMS dBFS, change from the previous section):
  - S1 bars 0-8: -10.9
  - S2 bars 9-40: -8.8 (+2.1 dB)
  - S3 bars 41-48: -17.1 (-8.3 dB)
  - S4 bars 49-56: -15.0 (+2.1 dB)
  - S5 bars 57-120: -9.0 (+6.0 dB)
  - S6 bars 121-130: -9.6 (-0.6 dB)
- Every 8 bars (RMS dBFS): 1-8: -11 | 9-16: -9 | 17-24: -9 | 25-32: -9 | 33-40: -9 | 41-48: -17 | 49-56: -15 | 57-64: -9 | 65-72: -9 | 73-80: -9 | 81-88: -9 | 89-96: -9 | 97-104: -9 | 105-112: -9 | 113-120: -9 | 121-128: -10 | 129-130: -10

## 6. Splice brief

Track facts for every search: **126 BPM**, **G minor (6A)** or **D# major (5B)** (unconfirmed). Each row is a gap trackcard measured, with the evidence. Use the BPM range and key as Splice filters, the layer as the instrument type, and try the candidate tags in order. Ask the producer before replacing anything that is already there.

### 1. S1, bars 0-8: bass
- Gap: no bassline in a peak-energy section
- Evidence: bass stem absent; section level -2.1 dB vs the loudest section
- BPM range: 124-128
- Key: G minor (6A) or D# major (5B); trackcard is unsure between the two, so confirm with the producer; also works: D minor (7A), C minor (5A), A# major (6B)
- Layer type: bass
- Candidate Splice tags: basslines, bass loops, sub bass, synth bass
- Do this: Search Splice for bass loops at 124-128 BPM, key G minor (or D# major), tags: basslines, bass loops, sub bass. Use it in bars 0-8 to anchor the low end.

### 2. S4, bars 49-56: fx
- Gap: nothing builds into the next section
- Evidence: next section is 6.0 dB louder
- BPM range: 124-128
- Key: any (unpitched; skip the key filter)
- Layer type: fx
- Candidate Splice tags: risers, uplifters, sweeps, white noise, fx
- Do this: Search Splice for fx samples at 124-128 BPM, tags: risers, uplifters, sweeps. Use it in bars 49-56 to build into the next section (last 4-8 bars).
