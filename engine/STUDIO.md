# The Studio (engine/STUDIO.md)

The playbook for a Claude session that turns a production brief into moves on Splice, Suno, Epidemic Sound and Spotify,
and records what Krish or Calvin picked. Code: `src/trackcard/studio/`; commands: `trackcard studio ...`. Asked for by
Krish on 2026-11-24 ("connect Suno, Splice, Epidemic, Spotify ... without losing sight of what we built for what purpose").

## Where it sits

| Part | Its one job | It never |
|---|---|---|
| **Brains** (`taste/`, `taste/calvin/`) | Hold what each person likes; rules live only in each `APPROVED.md` | Act on a tool |
| **Engine** (`engine/`) | Collect bounces and drops, measure them, write one brief per project | Decide taste, call a tool |
| **Studio** (this) | Propose tool moves for a brief, compare outside measurements with trackcard's, keep a ledger of picks | Pick for a person, spend without a yes, use one brain's rules for the other person |

The connectors live in Claude sessions, not on the worker. So the code computes moves, comparisons and edit maths, and
a session runs them. Every move is in `brief.json` under `moves` (and in BRIEF.md, "Studio moves"), or from
`trackcard studio moves <project>`.

## Gates

| Gate | What | Rule |
|---|---|---|
| `free` | Splice search, Epidemic search and previews, Suno analysis | Run it. Show every result, numbered, and let the person choose. |
| `standing_yes` | Uploading a new bounce **privately** to Suno for its analysis | **Ruling (Krish, 2026-11-24):** every new bounce, Krish's and Calvin's, may be uploaded for analysis; Krish confirms Calvin agrees. Nothing else rides on it. |
| `yes_each` | Splice `download_asset` (1 credit), Suno `sounds-create` (2), `audio-create` (song price), `audio-midi` (10), `audio-stems-create` (10 or 50), Spotify `generate_playlist`, Epidemic `DownloadRecording` and `EditRecording` | Quote the exact call and its cost, then wait for a yes for that call. A yes never carries to the next call. |

Spend is checked live: read Suno `account-usage` before and after a paid call and record the credits with the pick.
Epidemic is on the Creator plan: Krish's own channels, never paid ads (Ruling, Krish, 2026-10-26).

## The five moves

1. **Second ear (Suno, `suno_second_ear`).**
   - **Steps:** download the bounce from Drive, outside the repository. Upload it with `audio-upload-create`, or give the
     person the `upload_page_url`. Then call `audio-upload-complete` and poll `audio-analysis` until it leaves
     `processing`.
   - **Stop and say so** if the song's `visibility` is not private.
   - **Then:** save the analysis JSON outside the repository and run
     `trackcard studio ear <project> --analysis <file>`. It writes `engine/productions/<project>/ear/<version>.json`
     (the comparison only).
   - **What the engine does with it:** the next run puts every disagreement in STATUS as an **ear-check**. Tempo
     counts as a disagreement past 0.5 BPM after octave correction; key when it is neither the same nor relative; the
     bar grid past a quarter beat; a section boundary past 1 bar. People listen only there.
   - **Never write down** the Suno id or link.
2. **Splice search (`splice_search`).**
   - **Plain query first.** It is the brief's own query, which carries the key for pitched layers.
   - **Character variant second,** only when the move's owner has an accepted rule for that layer.
   - **Measured 2026-11-24:**
     - "bass basslines G minor" gave 10 of 10 bass loops, 9 of 10 in G.
     - "growly characterful bassline G minor" gave bass loops, none in G. So character results are filtered by
       `post_filter.keys` before they are shown.
     - Genre words drown the instrument: "brass stab loop" gave 10 of 10 brass, but the same words with "melodic house"
       gave none. Never add genre words.
   - **Downloads** spend a credit: ask for that exact sound. Stacks only around a loop, with `generate_public_url: false`.
3. **Notes, not sounds (`suno_sketch_midi`, `suno_sound`).**
   - **Sketch:** for a pitched gap, `audio-create` makes 8-bar instrumental ideas at the project's exact tempo and key.
     The person picks one, or none, and `audio-midi` transcribes it.
   - **MIDI only:** only the MIDI goes to Ableton, to be played with their own sounds. The sketch audio never enters the
     track.
   - **Fallback:** `sounds-create` makes a loop at the project's tempo and key, for when Splice has nothing.
4. **Pro twin (Epidemic, `epidemic_twin`).**
   - **Find it:** for a reference that fits the project, `SearchRecordings` by its Spotify id returns catalog tracks
     with drums, bass, melody and instruments stems. Take the one nearest the project's tempo.
   - **Measure it:** run `trackcard analyze --no-stems` on the full-mix preview and on each stem preview, outside the
     repository.
   - **Record it:**
     `trackcard studio twin <project> --recording rec.json --full full.trackcard.json --stem bass=bass.trackcard.json ...`.
     It writes `engine/productions/<project>/twins/<recording id>.json`.
   - **In the brief:** when each layer comes in, against ours, to the nearest 8 bars.
5. **Drop on the cut (Epidemic, for the content engine).**
   - **Measure the track:** a licensed track chosen for a video is measured with trackcard, with stems for real drops.
   - **Compute the edit:** `trackcard studio cut --card track.trackcard.json --length 30 --hit 12.4 --recording-id <id>`
     prints the `EditRecording` input. It lands the main drop on the reveal at 12.4 s, with whole bars of build before
     it.
   - **Run it** with a yes, then record the recording id with the asset (the content engine's rule).
   - **Why:** this is the North Star's stated purpose, audio treatment for the content engine.

Plus **revealed taste (Spotify):**

- **Read:** read the person's own most-played tracks with Spotify `search` ("my most played tracks"). It is read-only.
- **Write:** `trackcard studio revealed --who krish --rows rows.json` writes `engine/references/krish/revealed.csv`.
- **What it keeps:** the link, title, artists and rank band (`top50` or `top200`) only; no play counts and no timestamps
  (Krish's decision, 2026-11-24).
- **What the engine does:** it measures those tracks like drops, and they count in that person's measured layer only.
  Only Krish's Spotify is connected, so Calvin's brain never sees it.

## Record every pick

```bash
trackcard studio record closure --move m-1a2b3c4d --who krish --pick splice:<asset uuid> --title "<file name>" --credits 1
trackcard studio record closure --move m-5e6f7a8b --who calvin --suno-clip <clip id> --credits 20   # only its hash is kept
trackcard studio record closure --move m-1a2b3c4d --who krish --pick none --note "nothing fit"
```

Rows go to `engine/productions/<project>/moves.jsonl`. When the next bounce's diff closes that gap, the brief says
which pick it followed (`closed_by`). STATUS shows the North Star: **gaps closed per bounce** (Krish, 2026-11-24), with
how many came after a Studio pick. Commit Studio files through a PR that Krish merges, like any other change.

## Never

- Commit audio, a Suno id or link, a presigned download or upload URL, a Drive id, or an email. The privacy gate (now
  with `suno_link` and `signed_url`) and the ledger refuse them.
- Use one brain's rules for the other person, or treat a proposal as a rule.
- Treat a tool's output as the track. Suno sketches are references; picks are the person's.
