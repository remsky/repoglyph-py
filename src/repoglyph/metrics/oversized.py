"""Flag oversized source files; candidates for splitting."""

from __future__ import annotations

from repoglyph.metrics.base import Finding, code_cell, fmt_bytes
from repoglyph.metrics.core import OVERSIZED_FILE_BYTES
from repoglyph.models import CityData
from repoglyph.palette import categorize

__all__ = ["OVERSIZED_FILES"]


def _oversized_files(data: CityData) -> list[tuple[str, ...]]:
    offenders = sorted(
        (f for f in data.files if categorize(f.path) == "code" and f.size > OVERSIZED_FILE_BYTES),
        key=lambda f: (-f.size, f.path),
    )
    return [(code_cell(f.path), fmt_bytes(f.size)) for f in offenders]


OVERSIZED_FILES = Finding(
    key="oversized_files",
    title="Oversized source files",
    blurb=f"Code files over {fmt_bytes(OVERSIZED_FILE_BYTES)}; candidates for splitting.",
    columns=("file", "size"),
    compute=_oversized_files,
)
