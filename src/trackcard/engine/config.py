"""Worker configuration. Folder ids and emails live here, on the worker, never in the repository."""
from __future__ import annotations

import json
import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PATH = "~/.music-watcher/engine.json"


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    clone: Path
    inspiration_folders: tuple[str, ...] = ()
    productions_folder: str = ""
    people: dict = field(default_factory=dict)  # lowercased email -> "krish" | "calvin"
    state_dir: Path = Path("~/.music-watcher/engine").expanduser()
    work_dir: Path = Path("~/media/engine").expanduser()
    remote: str = "gdrive"
    rclone: str = "rclone"
    trackcard: str = "trackcard"
    ytdlp: str = "yt-dlp"
    ffmpeg: str = "ffmpeg"
    gh: str = "gh"
    max_per_run: int = 3
    max_download_mb: int = 400
    budget_s: int = 3000
    sheet_title: str = "Calvin and Krish - Spotify tracks"
    branch: str = "engine/updates"
    base: str = "main"

    @property
    def cache(self) -> Path:
        return self.state_dir / "cache"

    @property
    def state_file(self) -> Path:
        return self.state_dir / "state.json"

    @property
    def journal(self) -> Path:
        return self.state_dir / "journal.log"

    def tool(self, name: str) -> list[str]:
        return shlex.split(getattr(self, name))

    def private_values(self) -> set[str]:
        """Values that must never reach a public file: folder ids and the people's emails."""
        vals = {f for f in self.inspiration_folders if f} | ({self.productions_folder} if self.productions_folder else set())
        return vals | {e for e in self.people if e}


def _inside(p: Path, root: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def load(path: str | Path | None = None, *, clone: Path | None = None, require_drive: bool = True) -> Config:
    """Read the worker config. `clone` overrides the file's (tests and dry runs)."""
    p = Path(os.path.expanduser(str(path or os.environ.get("ENGINE_CONFIG") or DEFAULT_PATH)))
    raw: dict = {}
    if p.exists():
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ConfigError(f"engine config is not valid JSON ({e.msg} at line {e.lineno})") from None
    elif require_drive:
        raise ConfigError(f"no engine config at {p} (copy engine/config.example.json there and fill it in)")
    root = Path(os.path.expanduser(str(clone or raw.get("clone") or "."))).resolve()
    kw = {k: raw[k] for k in ("remote", "rclone", "trackcard", "ytdlp", "ffmpeg", "gh", "max_per_run",
                              "max_download_mb", "budget_s", "sheet_title", "branch", "base") if k in raw}
    for k in ("state_dir", "work_dir"):
        if k in raw:
            kw[k] = Path(os.path.expanduser(raw[k]))
    folders = raw.get("inspiration_folders") or []
    cfg = Config(clone=root, inspiration_folders=tuple(folders), productions_folder=raw.get("productions_folder", ""),
                 people={str(k).strip().lower(): v for k, v in (raw.get("people") or {}).items()}, **kw)
    for who in cfg.people.values():
        if who not in ("krish", "calvin"):
            raise ConfigError("people values must be krish or calvin")
    for name, d in (("state_dir", cfg.state_dir), ("work_dir", cfg.work_dir), ("config", p)):
        if _inside(d, root):
            raise ConfigError(f"{name} must be outside the clone: the repository is public")
    if require_drive and not (cfg.productions_folder and cfg.inspiration_folders):
        raise ConfigError("productions_folder and inspiration_folders are required")
    return cfg
