"""Synthetic Drive listings for the engine tests. Every id, email and title here is invented; the ids and emails are the
sentinels the leak tests search for in everything the engine writes."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from trackcard.engine.config import Config

REPO = Path(__file__).resolve().parents[1]
TEMPLATE_CARD = REPO / "taste" / "inspo" / "cards" / "7DxrTNmUprBMQ0RV45xreb.trackcard.json"
KRISH, CALVIN, STRANGER = "krish.test@example.com", "calvin.test@example.com", "stranger.test@example.com"
PROD_FOLDER, INSP_FOLDER = "1ProdFolderSentinelAAAAAAAAAAAAA", "1InspFolderSentinelBBBBBBBBBBBBB"


def fake_id(n: int | str) -> str:
    return "1Fake" + hashlib.sha1(str(n).encode()).hexdigest()[:28]


def entry(n, name, path=None, owner=CALVIN, btime="2026-11-13T20:39:35Z", md5=None, mime="audio/wav",
          size=40_000_000, isdir=False, description="private note sentinel"):
    e = {"Path": path or name, "Name": name, "Size": -1 if isdir else size, "MimeType": mime,
         "ModTime": btime.replace("Z", ".123Z"), "IsDir": isdir, "ID": fake_id(n),
         "Metadata": {"owner": owner, "btime": btime.replace("Z", ".000Z"), "description": description}}
    if not isdir:
        e["Hashes"] = {"md5": md5 or hashlib.md5(str(n).encode()).hexdigest()}
    return e


def make_cfg(tmp: Path, clone: Path, **kw) -> Config:
    return Config(clone=clone, inspiration_folders=(INSP_FOLDER,), productions_folder=PROD_FOLDER,
                  people={KRISH: "krish", CALVIN: "calvin"}, state_dir=tmp / "state", work_dir=tmp / "work", **kw)


def make_clone(tmp: Path) -> Path:
    """A minimal checkout: the brains (for rules) and build_graph, no engine data yet."""
    clone = tmp / "clone"
    for rel in ("taste/brain", "taste/calvin/brain", "taste/graph/build_graph.py", "taste/APPROVED.md",
                "taste/calvin/APPROVED.md", "taste/graph/tracks.csv", "taste/calvin/graph/tracks.csv"):
        src, dst = REPO / rel, clone / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if src.is_dir() else shutil.copyfile)(src, dst)
    return clone


def card(vid: str, *, stems=True, duration=None, bpm=None, drop_bar=None, extra_gap=False) -> dict:
    c = json.loads(TEMPLATE_CARD.read_text())
    c["file"] = f"{vid}.wav"
    if duration:
        c["duration"] = duration
    if bpm:
        c["bpm"] = c["likely_project_bpm"] = bpm
    if drop_bar:
        for d in c["drops"]:
            if d.get("main"):
                d["bar"] = drop_bar
    if not stems:
        c["stems_available"] = False
        c["drops"], c["moments"] = [], []
        for s in c["sections"]:
            s["stems"] = None
        c["brief"] = [g for g in c["brief"] if g["rule"] in ("R4", "R7")]
    if extra_gap:
        g = copy.deepcopy(c["brief"][0])
        g.update(rule="R8", layer="pads", bars="90-98", gap="low-energy section is very bare")
        c["brief"].append(g)
    return c


class FakeMeasurer:
    """Stands in for trackcard: writes a card for each version id; can fail on demand."""

    def __init__(self, cards: dict | None = None, fail: set | None = None):
        self.cards, self.fail, self.calls = cards or {}, fail or set(), []

    def __call__(self, cfg, src, vid, out, bpm=None, key=None):
        self.calls.append(vid)
        assert src.exists(), "the source file must be downloaded first"
        src.unlink()
        if vid in self.fail:
            return None, "trackcard_failed_no_stems"
        c = self.cards.get(vid) or card(vid)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{vid}.trackcard.json").write_text(json.dumps(c, indent=2))
        (out / f"{vid}.trackcard.md").write_text(f"# Track card: {vid}.wav\n")
        return c, ""


def files_for(listing: dict, tmp: Path) -> dict:
    """Every production file downloads as a small dummy file."""
    out = {}
    for e in listing.get("productions", []) + listing.get("inspiration", []):
        if not e.get("IsDir"):
            f = tmp / "drive" / e["ID"]
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"RIFF")
            out[e["ID"]] = str(f)
    return out


def all_text(root: Path) -> str:
    return "\n".join(p.read_text(errors="replace") for p in root.rglob("*") if p.is_file() and ".git" not in p.parts)


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout
