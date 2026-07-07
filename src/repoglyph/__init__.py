"""Generate an isometric "repo city" banner (SVG) from a local git repository.

Encodes structure (skyline) and recent work (lit windows). Public entry points:
``gather_city_from_path`` (read) and ``render`` (draw); the CLI lives in
``repoglyph.cli``.
"""

from __future__ import annotations

from repoglyph.gitsource import CloneError, gather_city_from_path, git_available
from repoglyph.models import CityData, SourceFile
from repoglyph.render import render

__all__ = [
    "CityData",
    "CloneError",
    "SourceFile",
    "gather_city_from_path",
    "git_available",
    "render",
]

__version__ = "0.1.0"
