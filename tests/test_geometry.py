from __future__ import annotations

from repoglyph.geometry import (
    HEIGHT_CAP,
    TILE_H,
    TILE_W,
    Scene,
    building_height,
    fit_banner,
    iso,
)


def test_iso_projects_grid_axes_exactly() -> None:
    assert iso(0, 0) == (0, 0)
    assert iso(1, 0) == (TILE_W, TILE_H)
    assert iso(0, 1) == (-TILE_W, TILE_H)
    assert iso(1, 1) == (0, 2 * TILE_H)


def test_building_height_is_capped() -> None:
    assert building_height(0) > 0
    assert building_height(10**12) == HEIGHT_CAP
    assert building_height(100) <= building_height(10_000)


def test_fit_banner_fixed_canvas_and_full() -> None:
    scene = Scene(
        buildings=[],
        offset_x=12.0,
        offset_y=12.0,
        content_width=400.0,
        content_height=200.0,
    )

    # Fixed mode: canvas is exactly the requested size, content scaled to fit.
    fixed = fit_banner(scene, width=1280, height=400)
    assert (fixed.width, fixed.height) == (1280, 400)
    assert fixed.scale > 0
    assert fixed.panel_x < fixed.divider_x < fixed.legend_x < fixed.width

    # Full mode: 1:1 content, canvas grows to fit it.
    full = fit_banner(scene, full=True)
    assert full.scale == 1.0
    assert full.width > 0 and full.height > 0
