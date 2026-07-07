"""The ``RepoMetrics`` fingerprint and its stat-table rows."""

from __future__ import annotations

import os
from dataclasses import dataclass

from repoglyph.metrics.base import Stat
from repoglyph.models import CityData, SourceFile, group_by_district
from repoglyph.palette import categorize

__all__ = ["OVERSIZED_FILE_BYTES", "RepoMetrics", "STATS", "compute_metrics"]

#: Byte size above which a single source file starts eroding the modularity
#: score, and past which the oversized-file finding flags it.
OVERSIZED_FILE_BYTES = 40_000


@dataclass(slots=True)
class RepoMetrics:
    """Summary statistics describing how a repository is organized."""

    file_count: int
    dir_count: int
    max_depth: int
    largest_district: str
    largest_district_share: float
    contributor_count: int
    modularity: int
    #: Most recently active drawn district and its share of total churn. Filled
    #: by the renderer (which knows the drawn cut); ``None`` omits the panel line.
    active_district: str | None = None
    active_district_share: float = 0.0


def compute_metrics(data: CityData) -> RepoMetrics:
    """Derive the fingerprint metrics from gathered ``CityData``."""
    files = data.files
    file_count = len(files)

    districts = group_by_district(files)
    largest_district = max(districts, key=lambda name: len(districts[name])) if districts else ""
    largest_share = len(districts[largest_district]) / file_count if file_count else 0.0

    return RepoMetrics(
        file_count=file_count,
        dir_count=len({os.path.dirname(file.path) for file in files}),
        max_depth=max((file.depth for file in files), default=0),
        largest_district=largest_district,
        largest_district_share=largest_share,
        contributor_count=data.total_contributors,
        modularity=_modularity(files, largest_share),
    )


def _modularity(files: list[SourceFile], largest_share: float) -> int:
    """Score 0-100 rewarding balanced folders, penalizing giant source files."""
    code_files = [file for file in files if categorize(file.path) == "code"]
    biggest = max((file.size for file in code_files), default=0)
    raw = 100 * (1 - largest_share * 0.5) * (1 - (biggest / OVERSIZED_FILE_BYTES) * 0.04)
    return max(0, min(100, int(raw)))


# --------------------------------------------------------------------------
# fingerprint-table rows
# --------------------------------------------------------------------------
def _files(data: CityData, metrics: RepoMetrics) -> str:
    return f"{metrics.file_count:,}"


def _directories(data: CityData, metrics: RepoMetrics) -> str:
    return f"{metrics.dir_count:,}"


def _max_depth(data: CityData, metrics: RepoMetrics) -> str:
    return str(metrics.max_depth)


def _largest_district(data: CityData, metrics: RepoMetrics) -> str | None:
    if not metrics.largest_district:
        return None
    return f"{metrics.largest_district}, {metrics.largest_district_share:.0%} of files"


def _modularity_stat(data: CityData, metrics: RepoMetrics) -> str:
    return f"{metrics.modularity} / 100"


def _recent_activity(data: CityData, metrics: RepoMetrics) -> str:
    return f"{len(data.touches)} files touched in the last {data.commit_window} commits"


STATS: tuple[Stat, ...] = (
    Stat("files", "files", _files),
    Stat("directories", "directories", _directories),
    Stat("max_depth", "max depth", _max_depth),
    Stat("largest_district", "largest district", _largest_district),
    Stat("modularity", "modularity", _modularity_stat),
    Stat("recent_activity", "recent activity", _recent_activity),
)
