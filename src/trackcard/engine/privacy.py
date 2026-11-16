"""Nothing private reaches the public repository.

The repository is public and the Drive files are link-shared, so a Drive file id is a working download link to an
unreleased bounce and a folder id opens every bounce in it. Two tools:

  redact(text, secrets)  for anything that goes to the worker's own journal (never committed)
  scan(text, secrets)    the gate: the names of the rules a text breaks; publish refuses to commit or push on any hit

Failure reasons written to committed files are codes from WHY, never exception text or stderr.
"""
from __future__ import annotations

import re

WHY = {
    "download_failed", "export_failed", "timeout", "too_large", "convert_failed",
    "trackcard_failed_stems", "trackcard_failed_no_stems", "no_card",
    "spotify_page_incomplete", "no_soundcloud_match_within_6s", "youtube_needs_home", "private_link_needs_person",
    "playlist_link", "not_a_track_link", "no_link", "several_links",
    "brain_check_failed", "metadata_missing", "unexpected_error",
}

RULES = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("google_link", re.compile(r"(?:drive|docs)\.google\.com|googleusercontent\.com|/file/d/|[?&]id=[A-Za-z0-9_-]{10,}")),
    ("soundcloud_private", re.compile(r"soundcloud\.com/[^\s\"'<>]*/s-[A-Za-z0-9]+")),
    ("phone", re.compile(r"(?<![\w.])\+\d[\d ()-]{7,}\d")),
]
# Addresses that may appear in a commit (bot identities), never a person's.
ALLOWED_EMAILS = {"noreply@anthropic.com", "41898282+github-actions[bot]@users.noreply.github.com"}


def scan(text: str, secrets: set[str] | frozenset[str] = frozenset()) -> list[str]:
    hits = []
    for s in secrets:
        if s and len(s) >= 6 and s in text:
            hits.append("private_value")
            break
    for name, rx in RULES:
        found = [m.group(0) for m in rx.finditer(text)]
        if name == "email":
            found = [f for f in found if f.lower() not in ALLOWED_EMAILS]
        if found:
            hits.append(name)
    return hits


def redact(text: str, secrets: set[str] | frozenset[str] = frozenset()) -> str:
    for s in sorted((s for s in secrets if s and len(s) >= 6), key=len, reverse=True):
        text = text.replace(s, "<redacted>")
    for _, rx in RULES:
        text = rx.sub("<redacted>", text)
    return text


def why(code: str) -> str:
    """A failure reason fit for a committed file."""
    return code if code in WHY else "unexpected_error"
