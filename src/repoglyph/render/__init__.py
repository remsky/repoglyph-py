"""Render ``CityData`` to a standalone SVG string."""

from __future__ import annotations

from repoglyph.render.compose import render
from repoglyph.render.styles import STYLES, StyleParams, StyleSpec, district_set

__all__ = [
    "render",
    "STYLES",
    "StyleParams",
    "StyleSpec",
    "district_set",
]
