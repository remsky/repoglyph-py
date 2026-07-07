"""Persist CityData to a per-repo JSON snapshot and reload it."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from repoglyph.models import CityData, SourceFile

__all__ = ["CACHE_DIR", "repo_stem", "cache_path", "save_city", "load_city"]

#: Default directory (relative to the working directory) for cache snapshots.
CACHE_DIR = Path("repo_cache")

#: Bump if the serialized shape changes incompatibly.
_FORMAT_VERSION = 1

logger = logging.getLogger(__name__)


def repo_stem(repo: str) -> str:
    """Filesystem-safe filename stem for a repo label."""
    return re.sub(r"[^\w.-]", "_", repo)


def cache_path(repo: str, cache_dir: Path = CACHE_DIR) -> Path:
    """Return the cache file path for *repo* (``owner/repo`` -> one JSON file)."""
    return cache_dir / (repo_stem(repo) + ".json")


def save_city(data: CityData, cache_dir: Path = CACHE_DIR) -> Path:
    """Write *data* to the cache as JSON, overwriting any prior snapshot.

    Returns the path written.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_path(data.repo, cache_dir)

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


def load_city(repo: str, cache_dir: Path = CACHE_DIR) -> CityData:
    """Reconstruct ``CityData`` for *repo* from its cached JSON snapshot.

    Raises ``FileNotFoundError`` if no snapshot exists.
    """
    path = cache_path(repo, cache_dir)
    payload = json.loads(path.read_text(encoding="utf-8"))

    version = payload.get("format_version")
    if version != _FORMAT_VERSION:
        logger.warning(
            "cache %s has format_version %r (expected %d); loading anyway",
            path,
            version,
            _FORMAT_VERSION,
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
