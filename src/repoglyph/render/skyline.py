"""The "skyline" style: one windowed building per file in oblique's labelled districts."""

from __future__ import annotations

from repoglyph.geometry import (
    _CONTENT_PAD,
    _ROOF_MARGIN,
    TILE_H,
    TILE_W,
    PlacedBuilding,
    Scene,
    _build_tree,
    building_height,
    iso,
)
from repoglyph.models import SourceFile
from repoglyph.palette import CATEGORY_COLORS, Category
from repoglyph.palettes import DARK_CHROME, Chrome
from repoglyph.render.buildings import render_buildings
from repoglyph.render.scene import Tower, VoxelScene, _Cube, _pack_node, _PackConfig

__all__ = ["build_skyline", "render_skyline"]

type _Colors = dict[Category, tuple[str, str, str]]


def _building_tower(grid_x: int, grid_y: int, district: str, file: SourceFile) -> Tower:
    """One file as a single-cube tower sized to its full skyline (building) height."""
    height = building_height(file.size)
    return Tower(grid_x, grid_y, district, [_Cube(file, 0.0, height)], height)


def build_skyline(files: list[SourceFile], *, streets: int = 1) -> VoxelScene:
    """Pack files into the plot districts, one windowed building per file.

    Reuses the ``voxel``/``oblique`` plot packing (each file is one grid cell, so
    every tower holds a single building) but sizes the content box to the taller
    ``building_height`` and views it head-on (``view_rot=0``).
    """
    cfg = _PackConfig(streets=(streets, streets, 0), plot=True)
    block = _pack_node(_build_tree(files), "", 0, cfg)
    towers = [
        _building_tower(grid_x, grid_y, district, members[0])
        for grid_x, grid_y, district, members in block.cells
    ]

    xs: list[float] = []
    ys: list[float] = []
    for tower in towers:
        x, y = iso(tower.grid_x, tower.grid_y)
        xs += [x - TILE_W, x + TILE_W]
        ys += [y - tower.height - _ROOF_MARGIN, y + TILE_H]

    if xs:
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
    else:
        min_x = max_x = min_y = max_y = 0.0

    return VoxelScene(
        towers=towers,
        offset_x=_CONTENT_PAD - min_x,
        offset_y=_CONTENT_PAD - min_y,
        content_width=(max_x - min_x) + 2 * _CONTENT_PAD,
        content_height=(max_y - min_y) + 2 * _CONTENT_PAD,
        view_rot=0.0,
    )


def render_skyline(
    scene: VoxelScene,
    touches: dict[str, int],
    max_touch: int,
    *,
    colors: _Colors = CATEGORY_COLORS,
    chrome: Chrome = DARK_CHROME,
) -> str:
    """Draw each district tower as one windowed building."""
    buildings = [
        PlacedBuilding(tower.cubes[0].file, tower.grid_x, tower.grid_y) for tower in scene.towers
    ]
    proxy = Scene(
        buildings=buildings,
        offset_x=scene.offset_x,
        offset_y=scene.offset_y,
        content_width=scene.content_width,
        content_height=scene.content_height,
    )
    return render_buildings(proxy, touches, max_touch, colors=colors)
