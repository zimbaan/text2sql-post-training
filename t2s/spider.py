"""Spider benchmark: download (pinned + checksummed), load splits, and the SFT / DPO train split."""

from __future__ import annotations

import hashlib
import json
import random
import zipfile
from dataclasses import dataclass
from pathlib import Path

# SQLite databases + split files from the official Yale release, re-hosted so they can be pinned.
SPIDER_REPO = "HAL-9001/spider-databases"
SPIDER_REVISION = "4a01bbac6520cd35b216db9e1724e5e1ada60aa4"
SPIDER_SHA256 = "00636695dabed6b5f4b8328a16b13e069a2f16591d5efcce57660669c85b121b"

TRAIN_FILES = ("train_spider.json", "train_others.json")
DEV_FILES = ("dev.json",)


@dataclass(frozen=True)
class Example:
    id: str
    db_id: str
    question: str
    query: str


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_extract(zip_path: Path, dest: Path) -> None:
    dest = dest.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            target = (dest / member).resolve()
            if dest not in target.parents and target != dest:
                raise RuntimeError(f"Unsafe path in archive: {member}")
        zf.extractall(dest)


def find_root(data_dir: Path) -> Path | None:
    for candidate in (data_dir / "spider_data", data_dir / "spider", data_dir):
        if (candidate / "dev.json").exists() and (candidate / "database").is_dir():
            return candidate
    return None


def ensure_spider(data_dir: str | Path = "data") -> Path:
    """Return the Spider root folder, downloading and verifying it on first use."""
    data_dir = Path(data_dir)
    root = find_root(data_dir)
    if root:
        return root

    from huggingface_hub import hf_hub_download

    data_dir.mkdir(parents=True, exist_ok=True)
    zip_path = Path(
        hf_hub_download(
            repo_id=SPIDER_REPO,
            filename="spider_data.zip",
            repo_type="dataset",
            revision=SPIDER_REVISION,
            local_dir=data_dir,
        )
    )
    digest = _sha256(zip_path)
    if digest != SPIDER_SHA256:
        raise RuntimeError(f"Checksum mismatch for {zip_path}: {digest}")
    _safe_extract(zip_path, data_dir)
    zip_path.unlink()
    root = find_root(data_dir)
    if root is None:
        raise RuntimeError(f"Could not find dev.json and database/ under {data_dir} after extracting")
    return root


def db_file(root: Path, db_id: str) -> Path:
    return root / "database" / db_id / f"{db_id}.sqlite"


def load_split(root: Path, split: str) -> list[Example]:
    files = {"train": TRAIN_FILES, "dev": DEV_FILES}[split]
    examples: list[Example] = []
    for name in files:
        path = root / name
        if not path.exists():
            continue
        for i, row in enumerate(json.loads(path.read_text(encoding="utf-8"))):
            examples.append(
                Example(
                    id=f"{path.stem}-{i}",
                    db_id=row["db_id"],
                    question=row["question"].strip(),
                    query=row["query"].strip(),
                )
            )
    if not examples:
        raise FileNotFoundError(f"No {split} files found in {root}")
    return examples


def split_train(examples: list[Example], holdout: int, seed: int = 0) -> tuple[list[Example], list[Example]]:
    """Deterministically hold out `holdout` training questions for preference mining (never seen in SFT)."""
    if holdout <= 0:
        return list(examples), []
    rng = random.Random(seed)
    idx = list(range(len(examples)))
    rng.shuffle(idx)
    held = set(idx[:holdout])
    sft = [e for i, e in enumerate(examples) if i not in held]
    pref = [e for i, e in enumerate(examples) if i in held]
    return sft, pref


def subsample(examples: list[Example], fraction: float = 1.0, limit: int | None = None, seed: int = 0) -> list[Example]:
    out = list(examples)
    if fraction < 1.0:
        out = random.Random(seed).sample(out, max(1, round(len(out) * fraction)))
    if limit is not None:
        out = out[:limit]
    return out
