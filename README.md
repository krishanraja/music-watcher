# music-watcher

Krish and Calvin make electronic music together. This repository gives Claude what it needs to help them do that well:
**ears** (trackcard measures a bounce), **taste** (two Music Brains, one each, built only from evidence they approve), a
**production engine** (it collects what they make and what inspires them, and keeps one working brief per track) and a
**Studio** (it turns a brief into moves on Splice, Suno, Epidemic Sound and Spotify, and remembers what they picked).
Claude can't hear; this is how it listens, remembers what they like, and keeps track of where each production stands.

Where it stands right now is in [`NOW.md`](NOW.md); where it is going is in [`docs/ROADMAP.md`](docs/ROADMAP.md). How to
work in it (rules for sessions, provenance, privacy) is in [`AGENTS.md`](AGENTS.md). Its North Star, set by Krish on
2026-11-24, is **gaps closed per bounce** ([`docs/NORTH_STAR.md`](docs/NORTH_STAR.md)).

## What's here

| Part | What it does | Start with |
|---|---|---|
| **trackcard** (`src/trackcard/`) | Reads a WAV bounce locally and writes a card: tempo, key, a bar-numbered section map, stems per section, frequency balance, loudness, drops and layer changes, and a Splice brief of sounds that would fill measured gaps. CLI and MCP server. | [trackcard](#trackcard-claudes-ears) below |
| **Krish's Music Brain** (`taste/`) | Turns what Krish and Calvin say about tracks, plus measurements of Krish's 346-track playlist, into taste rules Krish approves one at a time. Only `taste/APPROVED.md` holds rules. | [`taste/graph/GENERATION.md`](taste/graph/GENERATION.md), [`taste/APPROVED.md`](taste/APPROVED.md) |
| **Calvin's Music Brain** (`taste/calvin/`) | The same machinery for Calvin: his 30-track playlist "Fall Bangers", his words only, his decisions only. | [`taste/calvin/README.md`](taste/calvin/README.md) |
| **The production engine** (`engine/`, `src/trackcard/engine/`) | Reads Drive's Music Production folder: decides whether each bounce is a new track or a new version, measures it, says what changed, and writes one brief per project; turns Inspiration drops and the reasons sheet into references and evidence for the right brain. Publishes through one rolling PR. | [`engine/README.md`](engine/README.md) |
| **The Studio** (`src/trackcard/studio/`, `trackcard studio`) | Turns a brief into tool moves (Splice searches, Suno second ear, sketches to MIDI and loops, Epidemic pro twins, drop on the cut for videos, Spotify most-played as revealed taste), gated by cost, and keeps a ledger of picks so the next bounce's diff says which pick closed which gap. | [`engine/STUDIO.md`](engine/STUDIO.md) |
| **Shared taste notes** (`taste/PREFERENCES.md`) | A written synthesis of what both of them reach for, for an AI to read next to a card. Evidence, not rules. | [`taste/PREFERENCES.md`](taste/PREFERENCES.md) |
| **Music Inspo** (`taste/inspo/`) | The first drop watcher. Replaced by the engine (Krish's ruling, 2026-11-16); its cards stay. | [`taste/inspo/README.md`](taste/inspo/README.md) |

## How it fits together

```text
 Drive: Music Production            Drive: Inspiration (+ the reasons sheet)        a session: "I love the bass on this"
          |                                       |                                                 |
          v                                       v                                                 v
   production engine  --measures with-->  trackcard  <--measures--  references         taste/brain/evidence.jsonl
          |                                                              |                    (their words, one shared log)
          |                                                              v                                 |
          |                                              engine/references/<who>/tracks.csv               |
          |                                                              |                                 |
          |                                                              v                                 v
          |                                      Krish's brain (taste/)          Calvin's brain (taste/calvin/)
          |                                      patterns -> proposals -> Krish accepts   ... -> Calvin accepts
          |                                                  |                                 |
          |                                                  v                                 v
          +------ reads approved rules only ------  taste/APPROVED.md            taste/calvin/APPROVED.md
          v
 engine/productions/<project>/BRIEF.md + brief.json   -->  people, Claude, the Studio (Splice, Suno, Epidemic; picks in
                                                              moves.jsonl, credited on the next bounce), later Ableton, a UI
```

The brains decide what counts as their taste (only through an accepted claim); the engine never decides one. The engine
reads the brains; the brains read the engine's measurements of each person's own drops.

## Use cases

| You want to | Do this | You get |
|---|---|---|
| Know what a new bounce is doing | Put it in Drive › Music Production, e.g. `Closure 11.20.wav` | On the engine's next run: a card, and `engine/productions/closure/BRIEF.md` updated with what changed since the previous version |
| Hear Claude talk about a moment | "Bars 33-40 of the latest Closure feel empty" in a session | Claude reads the brief and card for those bars (sections, stems, bands) and answers from the measurement |
| Find sounds for a gap | Ask Claude to work through the brief's "Gaps to fill" | Splice searches at the right tempo and key, shaped for the Splice MCP; nothing downloaded without your yes |
| Share a track that inspires you | Drop a `.txt` with its Spotify link in Inspiration (add a sentence if you like) | A measured reference; it counts in *your* brain; your sentence is filed under your name |
| Say why you like a track | Add a row to the sheet: `Krish (20 Nov 2026): the build before the drop` | The words in the shared evidence log under the right voice, tagged and listed in the engine's PR to confirm |
| See what your taste is turning into | `trackcard brain propose` weekly, then `accept` or `reject` | At most 3 proposals a week, frozen once proposed; accepted ones become rules in `APPROVED.md` |
| Check a single bounce by hand | `trackcard analyze bounce.wav --print` (or the MCP tool in Claude Desktop) | The card, locally, in a few minutes |
| Check the measurement with a second ear | Ask a session to run the brief's `suno_second_ear` move (a private upload; standing yes) | Ear-check questions in STATUS only where Suno and trackcard disagree |
| See how a finished track builds the same thing | Run a brief's `epidemic_twin` move | When a catalog track close to your reference brings in each layer, next to yours |
| Put a drop on a video's reveal | `trackcard studio cut --card track.trackcard.json --length 30 --hit 12.4` | Epidemic EditRecording arguments that land the measured drop on the frame |
| Know if the work is moving | `trackcard studio score` (also at the top of `engine/STATUS.md`) | Gaps closed per bounce, and how many after a Studio pick |
| Tell the engine it got a file wrong | Add a line to `engine/productions/aliases.json` (STATUS gives you the line) | The version moves, gets a date, a note, or is ignored; cards never move |

## Capabilities and limits, in short

- **Measures** tempo (to 0.01 BPM on a steady grid), key with a second opinion, bar-addressable sections, drops and their
  build-ups (with stems), four-stem activity, five-band balance and LUFS. It does not *hear*: section labels are cluster
  numbers, keys can lean to a neighbour, and the vocal stem picks up vocal-like synths. Details: the trackcard reference
  below, "Limits".
- **Tracks productions** from file names and upload dates, asks instead of guessing when a name is ambiguous, and keeps
  every version's card. It needs the worker to run, and it can only read what the worker's Drive login can see.
- **Learns taste** only from their own words and their own playlists and drops, and only as fast as they accept claims.
  Auto-tagged words are my read (Claude's) until confirmed.
- **Keeps private things private** in a public repository: no audio, no Drive ids or links, no emails, ever; a gate blocks
  them before every engine commit.
- **Acts through sessions:** a Claude session runs a brief's Studio moves on Splice, Suno, Epidemic and Spotify, free ones
  first and every credit asked for ([`engine/STUDIO.md`](engine/STUDIO.md)). It **does not yet** drive Ableton or have a
  UI ([`docs/ROADMAP.md`](docs/ROADMAP.md)).

---

## trackcard: Claude's ears

Claude can't hear. trackcard listens for it.

`trackcard analyze bounce.wav` reads a WAV bounce on your own computer and writes `bounce.trackcard.md`: a plain-text card with the tempo, key, a bar-numbered section map, which stems play in each section, the frequency balance, loudness, and a **Splice brief** of sounds that would fill measured gaps. Paste the card into a Claude chat (or let Claude call trackcard through MCP), point at a moment ("bars 17-24 feel empty"), and Claude can pick Splice sounds that fit the actual track.

Everything runs locally. No uploads, no API keys. The only network access is the one-time download of the Demucs model weights (about 80 MB) on first use.

### Install

Python 3.11 or newer. A CPU is enough; a CUDA or Apple Silicon GPU makes stem separation faster.

```bash
pip install "trackcard[stems,loudness] @ git+https://github.com/krishanraja/music-analyzer"
```

Or with uv:

```bash
uv tool install "trackcard[stems,loudness] @ git+https://github.com/krishanraja/music-analyzer"
```

Extras:

| extra | adds | without it |
|---|---|---|
| `stems` | PyTorch + Demucs (htdemucs stem separation) | sections 3 and part of 6 are skipped, and the card says so |
| `loudness` | pyloudnorm (integrated LUFS, ITU-R BS.1770) | RMS dBFS only, and the card says so |
| `sections` | allin1 (functional section labels) | Laplacian segmentation with `section_N` labels, and the card says so |

allin1 is best-effort. It needs `madmom` (install it from GitHub: `pip install git+https://github.com/CPJKU/madmom`) and NATTEN 0.17.x built for your exact PyTorch version, which is often hard to install, especially on CPU. If `import allin1` fails for any reason, trackcard falls back and names the reason in the card.

### Use

```bash
trackcard analyze path/to/bounce.wav            # writes path/to/bounce.trackcard.md
trackcard analyze bounce.wav --json             # also writes bounce.trackcard.json
trackcard analyze bounce.wav --out cards/       # write the card into another folder
trackcard analyze bounce.wav --no-stems         # skip Demucs (fast, less detail)
trackcard analyze bounce.wav --sections laplacian   # force the fallback segmenter
trackcard analyze bounce.wav --print            # also print the card to the terminal
trackcard analyze bounce.wav --bpm 125 --key Dm # you already know these: the card uses yours
```

**If you know the tempo or key, say so.** `--bpm` fits the bar grid at exactly that tempo; `--key` accepts `D minor`, `Dm`, `F# major`, `Bb` or a Camelot code like `7A`. The card and the Splice brief then use your values, and still show what trackcard measured next to them.

Accepted files: `.wav`, `.wave`, `.aif`, `.aiff`, `.flac`, at least 5 seconds long. Bad input gets a plain error and a non-zero exit code (1 for a problem with the file, 2 for an unexpected error). Every fallback is printed as a `note:` line and listed at the top of the card.

**Speed.** On a 4-core CPU with no GPU, a 4-5 minute track takes about 3-4.5 minutes, most of it Demucs. `--no-stems` takes well under a minute.

**Bounce tip.** Export from bar 1 of the arrangement. When a file starts with sound on a beat, trackcard treats that beat as bar 1, so its bar numbers match the DAW's.

### What's in the card

1. **Basics.** Duration; BPM plus the likely whole-number project tempo, with a confidence note (or your value, if you gave one); 4/4 (assumed); how bar 1 was chosen; key with major/minor and its Camelot code, with a confidence level and the runner-up key; when trackcard is unsure, a second likely key and why; harmonically compatible keys (Camelot neighbours and relative key).
2. **Section map.** One row per section: label, bar range, time range, length, and energy (the section's RMS level against the loudest section: peak, mid or low). The method line says whether labels came from allin1 or the Laplacian fallback. Below it, **Drops and layer changes**: every drop (with the main one marked) and, bar by bar, every layer that enters, leaves, fills out or pulls back. Drops are often staged (bassline or kick first, hats a few bars later), and the card says so. The section map gets a boundary at each drop.
3. **Stem activity.** Demucs htdemucs splits the bounce into drums, bass, vocals and other. Per section and stem: *active* (sounding in 45% or more of the section's 100 ms frames), *sparse* (10-45%), or *absent*, with the percentage. A frame counts as sounding when the stem is louder than -50 dBFS and within 30 dB of its own loud moments.
4. **Frequency balance per section.** Energy in sub (20-60 Hz), low (60-250 Hz), mid (250 Hz-2 kHz), high-mid (2-8 kHz) and air (8-20 kHz), in dB relative to the section's loudest band, measured at the file's native sample rate. Plain flags such as "nothing above 8 kHz", "no sub", "thin low end", "sub-heavy", "mids are scooped", "dull presence range".
5. **Loudness and dynamics.** Peak dBFS, RMS dBFS, integrated LUFS (if pyloudnorm is installed), crest factor, clipped-sample count, level per section with the change from the previous one, and level every 8 bars.
6. **Splice brief.** One entry per gap, each with the gap in plain words, the measurement behind it, a BPM range (project tempo ±2), the key (plus the second likely key when there is one) with compatible alternatives (or "any" for unpitched layers), a layer type from Splice's instrument list, candidate tags, and a one-line instruction an AI with no context can follow. Sections with the same label that trigger the same rule share one entry.

The brief comes from fixed rules, applied per section, at most three per section. Missing drums or bass only count as a gap in peak sections, because quieter sections are often deliberate breakdowns:

| rule | condition | layer |
|---|---|---|
| R1 | drums absent in a peak section (within 3 dB of the loudest) | drums |
| R2 | bass absent in a peak section | bass |
| R3 | bass active but no sub (<60 Hz) in a peak section | bass (sub) |
| R4 | nothing or very little above 8 kHz, section within 8 dB of the loudest | percussion |
| R5 | drums only sparse in a peak section | percussion |
| R6 | mids scooped, or neither "other" nor "vocals" is active | chords (loud section) or pads |
| R7 | the next section is 4 dB or more louder | fx (risers into it) |
| R8 | at most one stem active in a section more than 3 dB below the loudest | pads |
| R9 | vocals absent in every section | vocals (one optional, track-level entry) |

Layer types are drawn from: drums, percussion, bass, guitar, keys, strings, vocals, chords, leads, pads, brass-and-woodwinds, synth, fx. The current rules use drums, percussion, bass, chords, pads, fx and vocals.

### Use it with Claude Desktop (MCP)

`trackcard mcp` runs a small MCP server on stdio with one tool, `analyze_track`. Its arguments: `path` (required, absolute path to the WAV), `stems` (default true), `sections` (`auto`, `allin1` or `laplacian`), `bpm` and `key` (optional, the producer's own values, same forms as the CLI), `include_json` (default false) and `save` (default true: also writes the `.trackcard.md` next to the WAV). It returns the card as text.

Add it to `claude_desktop_config.json`, using the full path to the `trackcard` executable (`which trackcard` shows it):

```json
{
  "mcpServers": {
    "trackcard": {
      "command": "/full/path/to/trackcard",
      "args": ["mcp"]
    }
  }
}
```

Stem separation on a CPU takes minutes. If Claude Desktop gives up waiting, ask it to call `analyze_track` with `"stems": false`, or run `trackcard analyze` in a terminal and paste the card.

### How it works

| what | method | fallback |
|---|---|---|
| audio | soundfile; mono 22.05 kHz copy for beats, key and sections; native-rate copy for spectrum and loudness | clear error for missing, unreadable, too-short or silent files |
| tempo | librosa beat tracking. If the BPM is outside 85-170, beat tracking is re-run with hints at x0.5, x2/3, x1.5 and x2, and the candidate whose beats hit the strongest onsets wins (out-of-range candidates are penalised). Then a fixed-grid search: every steady grid within ±2 BPM of the estimate, at every phase, is scored against the onset envelope of the whole file. If one grid scores at least 1.5x the median, it becomes the beat grid and BPM is read to 0.01 (refined by a line fit through the onset peaks it hits). DAW bounces have one exact tempo, so this is the normal path. | if no grid stands out (live playing, tempo changes), the tracked beats are kept, BPM is the slope of a line through them, and the card says no single grid fits |
| off-beat check | if the kick/bass band (<250 Hz) is 1.5x stronger half a beat after the tracked beats, the grid moves by half a beat | reported when it fires |
| bar 1 | if the file starts with sound within 50 ms and a beat sits within a quarter beat of it, that beat is bar 1 | otherwise beat 1 is the grid phase with the strongest kick/bass (<250 Hz) onsets; the card says which rule ran and warns when the two disagree |
| key | harmonic/percussive separation, chroma_cens on the harmonic part, RMS-weighted average, correlation with the 24 Krumhansl-Kessler profiles. If the relative major/minor scores are within 0.05, the louder tonic wins. Camelot code from the result. A second opinion from Temperley's profiles: if it ranks a closely related key (sharing at least 6 of 7 notes) in its top two and within 0.1 of its best, that key is shown as "also likely"; failing that, the Krumhansl-Kessler runner-up is shown when within 0.1. | tie-break and alternative are reported |
| sections | allin1 (labels such as intro, verse, chorus, break, drop) | Laplacian segmentation: beat-synchronous CQT recurrence matrix with path enhancement plus an MFCC timbre path, spectral clustering with k chosen by eigengap in 3-6, sections under 8 s merged into a neighbour. Boundaries snap to the nearest downbeat (within half a bar), then to a 4-bar phrase start (within one bar). |
| stems | Demucs htdemucs. With a GPU: shifts=2, then shifts=0 on out-of-memory, then CPU. Without a GPU: CPU, shifts=0. 10 Hz RMS and peak envelopes per stem. | if PyTorch/Demucs are missing or the model can't load, the card says so and the stem-based rules are skipped |
| loudness | pyloudnorm integrated LUFS | RMS dBFS |
| drops and layer changes | Per bar, the level of bass, vocals, other, and the drums stem split into kick (<150 Hz) and tops (>5 kHz). A layer changing by 6 dB or more against its previous 4 bars, held for 2 bars, is a moment (a one-bar pre-drop cut does not count). A drop is bass or kick jumping to its full level after 4 bars well below it (10 dB on average); layers rising in the next 16 bars join it (a second bass/kick rise within 4 bars is the same drop). Each drop gets a run-up: the cut (where the low end went out and stayed out) and the build (the earliest layer change in the 16 bars before the cut). The main drop is the last drop with a run-up before the final 15% of the track, an arrangement convention: staged drops are often mixed to the same level, so loudness can't tell them apart. | needs stems; with `--no-stems` the block says it is unavailable |

### Limits (read these)

- trackcard measures; it does not hear. Labels from the fallback segmenter are cluster numbers, not musical functions. Energy levels hint at where the drops are, but that is an inference.
- 4/4 is assumed. Tempo changes within a track are not modelled; one BPM is reported.
- Key comes from averaged harmony. When riffs lean on the 4th and 5th of the key (common in electronic music), a neighbouring key can score higher: on one test track the producer's D minor came out as G minor (with D minor named as the alternative) on one bounce, and as D major with G minor as the alternative on a later bounce. Use `--key` when you know it.
- Demucs often puts a sub-heavy bass drop into the drums stem's low band, so a bassline drop can read as "kick and low drums".
- The drop rule looks at layers, not loudness: a heavily mastered track can be equally loud before and after a drop, and the energy column will not show it.
- The vocals stem on an instrumental track often picks up vocal-like synths and leads. Treat "vocals active" as "something in the vocal range", not proof of a singer.
- Bar numbers depend on the bar-1 rule above. If the bounce starts mid-bar or with a pickup, numbers can be off by a beat or two; the card warns when its two downbeat signals disagree.
- The Splice brief's tags are candidates to try, not a fixed vocabulary.

### Tests

```bash
pip install -e ".[stems,loudness,dev]"
pytest -m "not slow"     # fast suite: synthetic audio only
pytest -m slow           # real Demucs run, plus the end-to-end test
```

The fast suite generates its own audio: click tracks at known tempos (including the half-time case), chord progressions in known keys and modes, and a three-part track with known boundaries and stems. The end-to-end test runs the full pipeline on the first WAV it finds in `tests/fixtures/`. That folder is gitignored, and so is every audio file: put your own bounce there, it will never be committed. With no WAV present the test is skipped and says why.

To check trackcard against your ear, add entries to `taste/ear-checks.json` (committed; it holds names, tempos, keys and timestamps, never audio), or to a private `tests/fixtures/truth.json` (gitignored), which overrides it:

```json
{"my_track.wav": {"bpm": 125, "key": "D minor", "events": {"3:04": "main drop", "3:20": "tops"}}}
```

`pytest -m slow` then asserts the BPM within 0.1, that your key is the main or alternative key, and that a peak-energy section starts within one bar of each drop time. You can also list moments: `"events": {"3:04": "main drop", "3:20": "tops", "2:15": "cut", "3:37": "build"}`. A layer name means that layer must rise within one bar; "cut" and "drop" match within one bar; "build" matches within four, because where a build starts is fuzzy. All misses are reported together.


## Licence and credits

MIT. See `LICENSE`, and `NOTICE` for attributions (Stem MCP's MCP server skeleton and Demucs approach, methods reimplemented from MixMind, Demucs, allin1, librosa, pyloudnorm).
