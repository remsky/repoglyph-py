"""Plain data structures describing the repository being drawn."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

__all__ = ["SourceFile", "CityData", "group_by_district", "filter_files"]

#: District name used for files that live at the repository root.
ROOT_DISTRICT = ".root"


@dataclass(slots=True)
class SourceFile:
    """A single file (blob) in the repository tree."""

    path: str
    size: int = 0

    @property
    def depth(self) -> int:
        """Number of directory levels below the repository root."""
        return self.path.count("/")

    @property
    def district(self) -> str:
        """Top-level folder, or ``ROOT_DISTRICT`` for root files."""
        head, _, tail = self.path.partition("/")
        return head if tail else ROOT_DISTRICT


@dataclass(slots=True)
class CityData:
    """Everything needed to render a banner, fully resolved and offline.

    ``touches`` maps a file path to a positive recent-activity weight over the
    last ``commit_window`` commits; the renderer normalises it, so only relative
    magnitude matters.
    """

    repo: str
    files: list[SourceFile] = field(default_factory=list)
    touches: dict[str, int] = field(default_factory=dict)
    commit_window: int = 0
    total_contributors: int = 0
    #: Short SHA of the HEAD commit, shown under the panel subtitle when present.
    head_sha: str | None = None
    #: Set when the touch sample is a partial (truncated) slice of the window.
    touch_truncated: bool = False


def group_by_district(files: list[SourceFile]) -> dict[str, list[SourceFile]]:
    """Group *files* by their top-level district, preserving insertion order."""
    districts: dict[str, list[SourceFile]] = {}
    for file in files:
        districts.setdefault(file.district, []).append(file)
    return districts


def _normalize_dir(spec: str) -> str:
    """Trim whitespace and strip leading/trailing slashes from a dir spec."""
    return spec.strip().strip("/")


def filter_files(
    files: list[SourceFile],
    touches: dict[str, int],
    *,
    start_dir: str = "",
    skip_dirs: Iterable[str] = (),
) -> tuple[list[SourceFile], dict[str, int]]:
    """Re-root to *start_dir* and/or prune *skip_dirs* from *files* and *touches*.

    Path-only transform. Returns the inputs unchanged when neither filter applies
    or the result is empty.
    """
    root = _normalize_dir(start_dir)
    skips = [d for d in (_normalize_dir(s) for s in skip_dirs) if d]
    if not root and not skips:
        return files, touches

    def reroot(path: str) -> str | None:
        if not root:
            return path
        if path == root:
            return None
        if path.startswith(f"{root}/"):
            return path[len(root) + 1 :]
        return None

    def skipped(path: str) -> bool:
        segs = path.split("/")
        for d in skips:
            if "/" in d:
                if path == d or path.startswith(f"{d}/"):
                    return True
            elif d in segs[:-1]:
                return True
        return False

    keep: dict[str, str] = {}
    for file in files:
        rerooted = reroot(file.path)
        if rerooted is None or skipped(rerooted):
            continue
        keep[file.path] = rerooted
    if not keep:
        return files, touches

    out_files = [SourceFile(keep[f.path], f.size) for f in files if f.path in keep]
    out_touches = {keep[p]: count for p, count in touches.items() if p in keep}
    return out_files, out_touches
