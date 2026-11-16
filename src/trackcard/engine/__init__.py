"""The production engine: Drive in, measured productions and briefs out.

Separate from the Music Brain (taste/). The brain holds what Krish and Calvin like; the engine collects what they make and
what they drop as inspiration, measures it with trackcard, and writes one brief per project (engine/productions/) that a
later UI and the Splice, Ableton and Suno MCPs read. It reads the brains' approved rules; it never decides one.

One run (run.py), a pure function of main's tree, the Drive listing and the worker's measurement cache:

  sources   list Drive read-only (rclone); every entry becomes an Item with an allowlist of fields at once
  names     classify each production file: a new track, a new version of a project, or a question for a person
  measure   at most N measurements per run, into a cache outside the clone
  words     (sheet, text drops) their words into the shared evidence log, references and the brain feed
  brief     per project BRIEF.md + brief.json, and engine/STATUS.md
  publish   the privacy gate, then one rolling PR on engine/updates

The repository is public and the Drive files are link-shared: a Drive id, folder id or email never reaches a commit,
branch, PR, log or note (privacy.py). See engine/README.md.
"""
