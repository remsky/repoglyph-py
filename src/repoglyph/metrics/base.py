"""Building blocks for registered metrics, plus shared value formatting."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from repoglyph.metrics.core import RepoMetrics
    from repoglyph.models import CityData

__all__ = ["Finding", "Stat", "code_cell", "fmt_bytes"]


@dataclass(frozen=True, slots=True)
class Stat:
    """One row of the fingerprint table: a label and a formatted value.

    ``compute`` returns the value cell, or ``None`` to omit the row.
    """

    key: str
    label: str
    compute: Callable[[CityData, RepoMetrics], str | None]


@dataclass(frozen=True, slots=True)
class Finding:
    """A ranked-table section: a heading, a one-line blurb, and rows.

    ``compute`` returns pre-formatted markdown cells, one tuple per row in
    display order; an empty list omits the whole section.
    """

    key: str
    title: str
    blurb: str
    columns: tuple[str, ...]
    compute: Callable[[CityData], list[tuple[str, ...]]]


def code_cell(path: str) -> str:
    """Wrap *path* in backticks, escaped for use inside a markdown table cell."""
    return "`" + path.replace("|", "\\|") + "`"


def fmt_bytes(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{int(value):,} B" if unit == "B" else f"{value:,.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")
