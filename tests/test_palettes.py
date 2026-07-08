from __future__ import annotations

import json

import pytest

from repoglyph.models import CityData, SourceFile
from repoglyph.palette import CATEGORY_COLORS
from repoglyph.palettes import DEFAULT_PALETTE, PALETTES, resolve_palette
from repoglyph.render import render


def _city() -> CityData:
    return CityData(
        repo="o/r",
        files=[
            SourceFile("src/app.py", size=4_200),
            SourceFile("README.md", size=300),
            SourceFile("assets/logo.png", size=50_000),
        ],
    )


def test_default_palette_resolves_to_neon_colors() -> None:
    assert resolve_palette(None).colors == CATEGORY_COLORS
    assert resolve_palette(DEFAULT_PALETTE).colors == CATEGORY_COLORS


def test_builtins_cover_every_category() -> None:
    for palette in PALETTES.values():
        assert set(palette.colors) == set(CATEGORY_COLORS)


def test_unknown_palette_raises() -> None:
    with pytest.raises(ValueError, match="unknown palette"):
        resolve_palette("does-not-exist")


def test_default_render_unaffected_by_palette_arg() -> None:
    city = _city()
    assert render(city) == render(city, palette=resolve_palette("neon"))


def test_alternate_palette_changes_output_deterministically() -> None:
    city = _city()
    neon = render(city, palette=resolve_palette("neon"))
    light = render(city, palette=resolve_palette("light"))
    assert light != neon
    assert render(city, palette=resolve_palette("light")) == light
    # The light "code" top color reaches the SVG; the neon one is gone.
    assert PALETTES["light"].colors["code"][0] in light
    assert CATEGORY_COLORS["code"][0] not in light
    # The light theme also flips the page background (chrome), not just faces.
    assert PALETTES["light"].chrome.bg[0] in light
    assert CATEGORY_COLORS["code"][0] not in light


def test_custom_file_palette_falls_back_per_category(tmp_path) -> None:
    spec = tmp_path / "mine.json"
    spec.write_text(
        json.dumps({"name": "mine", "colors": {"code": ["#111111", "#222222", "#333333"]}})
    )
    palette = resolve_palette(str(spec))
    assert palette.name == "mine"
    assert palette.colors["code"] == ("#111111", "#222222", "#333333")
    # Untouched categories keep the default.
    assert palette.colors["docs"] == CATEGORY_COLORS["docs"]


def test_custom_file_rejects_bad_triple(tmp_path) -> None:
    spec = tmp_path / "bad.json"
    spec.write_text(json.dumps({"colors": {"code": ["#111111", "#222222"]}}))
    with pytest.raises(ValueError, match="3 hex color"):
        resolve_palette(str(spec))
