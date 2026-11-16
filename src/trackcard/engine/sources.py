"""Drive, read-only. Every listing entry becomes an Item with an allowlist of fields the moment it is read.

An Item never carries the Drive id, the owner's email, the description or any other metadata: the id is hashed into
`key` and kept only in a private map used for downloads, and the owner email is turned into "krish", "calvin" or
"unknown" and dropped. A listed file without owner and created-time metadata stops the run (fail closed): without them
the engine cannot say who dropped what or when.

RcloneSource talks to Drive. FixtureSource reads the same rclone lsjson JSON from a file (tests and dry runs).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import Config

AUDIO_EXT = {".wav", ".wave", ".aif", ".aiff", ".flac", ".mp3", ".m4a", ".ogg", ".opus"}
TEXT_EXT = {".txt", ".url", ".webloc", ".md"}
DOC_MIME = "application/vnd.google-apps.document"
SHEET_MIME = "application/vnd.google-apps.spreadsheet"


class SourceError(Exception):
    """Carries a code from privacy.WHY, never a raw message."""


def key_of(drive_id: str) -> str:
    return hashlib.sha256(drive_id.encode()).hexdigest()[:12]


@dataclass(frozen=True)
class Item:
    key: str
    name: str
    folder: str  # inspiration | production | archive
    kind: str  # audio | text | sheet
    mime: str
    size: int
    btime: str
    mtime: str
    md5: str
    who: str  # krish | calvin | unknown

    @property
    def sig(self) -> str:
        return self.md5 or self.mtime

    @property
    def ext(self) -> str:
        return Path(self.name).suffix.lower()


@dataclass
class Listing:
    items: list[Item]
    ignored: int = 0  # files of a kind the engine does not read (zip, pdf, ...): counted, never named
    other_folders: int = 0  # files in Music Production subfolders other than Archive/ and the inspiration folder


def _kind(name: str, mime: str, folder: str, sheet_title: str) -> str | None:
    ext = Path(name).suffix.lower()
    if folder == "inspiration":
        if mime == SHEET_MIME or ext == ".csv" or mime == "text/csv":
            return "sheet" if Path(name).stem == sheet_title else None
        if mime == DOC_MIME or mime.startswith("text/") or ext in TEXT_EXT:
            return "text"
        return None
    if ext in AUDIO_EXT or mime.startswith("audio/"):
        return "audio"
    return None


class _Base:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._ids: dict[str, str] = {}  # key -> raw Drive id, in memory only

    def raw_ids(self) -> set[str]:
        return set(self._ids.values())

    def _item(self, e: dict, folder: str) -> Item | None:
        meta = e.get("Metadata") or {}
        kind = _kind(e.get("Name", ""), e.get("MimeType", ""), folder, self.cfg.sheet_title)
        if kind is None:
            return None
        if not meta.get("owner") or not meta.get("btime"):
            raise SourceError("metadata_missing")
        key = key_of(e["ID"])
        self._ids[key] = e["ID"]
        who = self.cfg.people.get(str(meta["owner"]).strip().lower(), "unknown")
        return Item(key=key, name=e["Name"], folder=folder, kind=kind, mime=e.get("MimeType", ""),
                    size=int(e.get("Size") or -1), btime=_z(meta["btime"]), mtime=_z(e.get("ModTime", "")),
                    md5=((e.get("Hashes") or {}).get("md5") or "").lower(), who=who)

    def _productions(self, entries: list[dict]) -> Listing:
        dirs = {e["Path"]: e.get("ID", "") for e in entries if e.get("IsDir")}
        skip = {p for p, i in dirs.items() if i in self.cfg.inspiration_folders}
        out, ignored, other = [], 0, 0
        for e in entries:
            if e.get("IsDir"):
                continue
            parts = e["Path"].split("/")
            if len(parts) == 1:
                folder = "production"
            elif len(parts) == 2 and parts[0] in skip:
                continue
            elif len(parts) == 2 and parts[0].lower() == "archive":
                folder = "archive"
            else:
                other += 1
                continue
            it = self._item(e, folder)
            if it is None:
                ignored += 1
            else:
                out.append(it)
        return Listing(out, ignored, other)

    def _inspiration(self, entries: list[dict]) -> Listing:
        out, ignored = [], 0
        for e in entries:
            if e.get("IsDir") or "/" in e.get("Path", e.get("Name", "")):
                continue
            it = self._item(e, "inspiration")
            if it is None:
                ignored += 1
            else:
                out.append(it)
        return Listing(out, ignored)

    def list(self) -> Listing:
        p = self._productions(self._list_productions())
        i = self._inspiration(self._list_inspiration())
        items = sorted(p.items + i.items, key=lambda it: (it.btime, it.key))
        return Listing(items, p.ignored + i.ignored, p.other_folders)


def _z(t: str) -> str:
    """Drive times as UTC to the second: 2026-11-13T20:39:35Z."""
    t = (t or "").replace("+00:00", "Z")
    return t[:19] + "Z" if len(t) >= 19 else t


class RcloneSource(_Base):
    def _rclone(self, *args: str, timeout: int = 300) -> subprocess.CompletedProcess:
        return subprocess.run([*self.cfg.tool("rclone"), *args], capture_output=True, text=True, timeout=timeout)

    def _lsjson(self, folder: str, depth: int) -> list[dict]:
        try:
            r = self._rclone("lsjson", f"{self.cfg.remote}:", "-R", "--max-depth", str(depth), "-M", "--hash",
                             "--drive-export-formats", "txt,csv", f"--drive-root-folder-id={folder}")
        except subprocess.TimeoutExpired:
            raise SourceError("timeout") from None
        if r.returncode != 0:
            raise SourceError("download_failed")
        return json.loads(r.stdout or "[]")

    def _list_productions(self) -> list[dict]:
        return self._lsjson(self.cfg.productions_folder, 2)

    def _list_inspiration(self) -> list[dict]:
        out = []
        for f in self.cfg.inspiration_folders:
            out += self._lsjson(f, 1)
        return out

    def download(self, item: Item, dest: Path) -> None:
        """By id, so two files with one name never get mixed up. Raises SourceError with a code."""
        if item.size > self.cfg.max_download_mb * 1_000_000:
            raise SourceError("too_large")
        dest.parent.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(dest.parent).free
        if item.size > 0 and item.size * 3 > free:  # the WAV conversion and Demucs need room too
            raise SourceError("too_large")
        try:
            r = self._rclone("backend", "copyid", f"{self.cfg.remote}:", self._ids[item.key], str(dest),
                             "--drive-export-formats", "txt,csv", timeout=1800)
        except subprocess.TimeoutExpired:
            raise SourceError("timeout") from None
        if r.returncode != 0 or not dest.exists():
            raise SourceError("download_failed")


class FixtureSource(_Base):
    """{"productions": [lsjson entries], "inspiration": [lsjson entries], "files": {"<ID>": "<text or local path>"}}"""

    def __init__(self, cfg: Config, path: Path | dict):
        super().__init__(cfg)
        self.data = path if isinstance(path, dict) else json.loads(Path(path).read_text(encoding="utf-8"))

    def _list_productions(self) -> list[dict]:
        return self.data.get("productions", [])

    def _list_inspiration(self) -> list[dict]:
        return self.data.get("inspiration", [])

    def download(self, item: Item, dest: Path) -> None:
        src = (self.data.get("files") or {}).get(self._ids[item.key])
        if src is None:
            raise SourceError("download_failed")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(src, dict) and "text" in src:
            dest.write_text(src["text"], encoding="utf-8")
        else:
            shutil.copyfile(src, dest)
