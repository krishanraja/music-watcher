# North Star

Status: Set by Krish, 2026-11-24
Owner: Krish Raja

**The number: gaps closed per bounce.** Each new version of a project is diffed against the one before it; the measured
gaps (the brief's "Gaps to fill") that the new bounce closes are counted, divided by the number of bounces compared. A
bounce counts when it and the version before it were both measured with stems, the only case where gaps are compared.
Alongside it: how many closed gaps came after a Studio pick for that gap (`closed_by`). Read it with
`trackcard studio score`, or at the top of `engine/STATUS.md`.

Chosen by Krish in a session on 2026-11-24 from four candidates (gaps closed per bounce; days between bounces; finished
tracks per quarter; content cuts timed by trackcard). No target is set yet; only Krish sets one. It is not measured until
the engine runs on the worker and a project has two stem-measured versions.

Only Krish changes this.

What the repository is for, in his words of 14 Nov 2026: the music engine "will become peripherally useful for my content engine as well, as we start making the audio treatment more sophisticated in my production content", used "in the same way the content watcher is". A number for that is his to choose.
