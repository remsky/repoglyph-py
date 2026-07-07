"""Persist CityData to a JSON snapshot in the output folder and reload it."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from repoglyph.models import CityData, SourceFile

__all__ = ["CACHE_NAME", "repo_stem", "save_city", "load_city"]

#: Snapshot filename inside the output folder.
CACHE_NAME = "cache.json"

#: Bump if the serialized shape changes incompatibly.
_FORMAT_VERSION = 1

logger = logging.getLogger(__name__)


def repo_stem(repo: str) -> str:
    """Filesystem-safe filename stem for a repo label."""
    return re.sub(r"[^\w.-]", "_", repo)


def save_city(data: CityData, out_dir: Path) -> Path:
    """Write *data* to ``out_dir/cache.json``, overwriting any prior snapshot."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / CACHE_NAME

    payload = {
        "format_version": _FORMAT_VERSION,
        "repo": data.repo,
        "commit_window": data.commit_window,
        "files": [{"path": f.path, "size": f.size} for f in data.files],
        "touches": data.touches,
        "total_contributors": data.total_contributors,
        "head_sha": data.head_sha,
        "touch_truncated": data.touch_truncated,
    }

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("cached structural data to %s", path)
    return path


def load_city(out_dir: Path) -> CityData:
    """Reconstruct ``CityData`` from ``out_dir/cache.json``.

    Raises ``FileNotFoundError`` if absent, ``ValueError`` if incompatible.
    """
    path = out_dir / CACHE_NAME
    payload = json.loads(path.read_text(encoding="utf-8"))

    version = payload.get("format_version")
    if version != _FORMAT_VERSION:
        raise ValueError(
            f"cache {path} has format_version {version!r} (expected {_FORMAT_VERSION}); "
            "refresh it by running with --cache"
        )

    return CityData(
        repo=payload["repo"],
        files=[SourceFile(path=f["path"], size=f["size"]) for f in payload["files"]],
        touches=dict(payload["touches"]),
        commit_window=payload["commit_window"],
        total_contributors=payload.get("total_contributors", 0),
        head_sha=payload.get("head_sha"),
        touch_truncated=payload.get("touch_truncated", False),
    )
