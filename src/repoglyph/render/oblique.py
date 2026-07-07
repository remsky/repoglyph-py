"""Cabinet-oblique "map" city style (``--style oblique``)."""

from __future__ import annotations

from dataclasses import dataclass

from repoglyph.geometry import _CONTENT_PAD, _build_tree
from repoglyph.models import SourceFile
from repoglyph.palette import CATEGORY_COLORS, Category, categorize
from repoglyph.render.lighting import window_light
from repoglyph.render.scene import (
    _FACE_DIM,
    _OBLIQUE,
    _ROOF_WIN,
    Tower,
    _make_tower,
    _pack_node,
    _PackHints,
    _scale,
)

__all__ = [
    "ObliqueParams",
    "ObliqueScene",
    "build_oblique",
    "render_oblique",
]

type _Colors = dict[Category, tuple[str, str, str]]


@dataclass(frozen=True, slots=True)
class ObliqueParams:
    """The cabinet-oblique camera parameters."""

    cell_w: float = 20.0
    cell_d: float = 12.0
    cell_shear: float = 2.0
    height_scale: float = 0.65


#: The flat, map-like camera (low shear); default oblique look.
_FLAT = ObliqueParams()

#: Width bias passed to the shared shelf packer (higher equals wider shelves).
_OBLIQUE_ASPECT = 2.8


def _ground(gx: float, gy: float, p: ObliqueParams) -> tuple[float, float]:
    """Project a grid corner to its screen point on the ground plane (no offset).

    Grid-x is horizontal; grid-y (depth) recedes by ``(p.cell_shear, p.cell_d)``
    per row. Height is applied separately (straight up) by the cube drawing.
    """
    return gx * p.cell_w + gy * p.cell_shear, gy * p.cell_d


@dataclass(slots=True)
class ObliqueScene:
    """Oblique city scene representation in content coordinates."""

    towers: list[Tower]
    offset_x: float
    offset_y: float
    content_width: float
    content_height: float
    #: HEAD-bias pack hints used for de-flickered timelapses.
    pack_hints: _PackHints | None = None
    #: Camera this scene was packed/measured for; every drawer reads it back.
    params: ObliqueParams = _FLAT

    @classmethod
    def build(
        cls,
        files: list[SourceFile],
        hints: _PackHints | None = None,
        *,
        params: ObliqueParams = _FLAT,
    ) -> ObliqueScene:
        """Pack files (reusing voxel-plot packing) and size the scene box."""
        record = _PackHints({}, {}, {}, {})
        block = _pack_node(_build_tree(files), "", 0, _OBLIQUE, _OBLIQUE_ASPECT, hints, record)
        towers = [
            _make_tower(grid_x, grid_y, district, members)
            for grid_x, grid_y, district, members in block.cells
        ]

        xs: list[float] = []
        ys: list[float] = []
        for tower in towers:
            gx, gy = tower.grid_x, tower.grid_y
            for cx, cy in ((gx, gy), (gx + 1, gy), (gx, gy + 1), (gx + 1, gy + 1)):
                px, py = _ground(cx, cy, params)
                xs.append(px)
                # Ground point and, for the back corners, the extruded roof above.
                ys += [py, py - tower.height * params.height_scale]

        if xs:
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
        else:  # empty repo; keep a valid, tiny box
            min_x = max_x = min_y = max_y = 0.0

        return cls(
            towers=towers,
            offset_x=_CONTENT_PAD - min_x,
            offset_y=_CONTENT_PAD - min_y,
            content_width=(max_x - min_x) + 2 * _CONTENT_PAD,
            content_height=(max_y - min_y) + 2 * _CONTENT_PAD,
            pack_hints=record,
            params=params,
        )


def build_oblique(
    files: list[SourceFile], *, shear: float = 2.0, hints: _PackHints | None = None
) -> ObliqueScene:
    """Oblique style builder for the cabinet-oblique projection."""
    return ObliqueScene.build(files, hints, params=ObliqueParams(cell_shear=shear))


def render_oblique(
    scene: ObliqueScene,
    touches: dict[str, int],
    max_touch: int,
    *,
    colors: _Colors = CATEGORY_COLORS,
) -> str:
    """Render every cube, painter-sorted back-to-front."""
    ordered = sorted(scene.towers, key=lambda tower: (tower.grid_y, -tower.grid_x))
    body = "".join(_tower(tower, scene, touches, max_touch, colors) for tower in ordered)
    return f"<g>{body}</g>"


def _tower(
    tower: Tower,
    scene: ObliqueScene,
    touches: dict[str, int],
    max_touch: int,
    colors: _Colors,
) -> str:
    """Draw one tower as a bottom-to-top stack of file-cubes."""
    last = len(tower.cubes) - 1
    return "".join(
        _cube(
            tower.grid_x,
            tower.grid_y,
            cube,
            scene,
            touches,
            max_touch,
            roof=index == last,
            colors=colors,
        )
        for index, cube in enumerate(tower.cubes)
    )


def _poly(points: list[tuple[float, float]], fill: str, stroke: str) -> str:
    """An SVG polygon from screen points."""
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}" {stroke}/>'


def _roof_window(top: list[tuple[float, float]], *, fill: str, opacity: float) -> str:
    """Inset a lit quad on a cube's roof (top face shrunk toward its centre)."""
    cx = sum(p[0] for p in top) / 4
    cy = sum(p[1] for p in top) / 4
    pts = " ".join(
        f"{cx + _ROOF_WIN * (x - cx):.1f},{cy + _ROOF_WIN * (y - cy):.1f}" for x, y in top
    )
    return f'<polygon points="{pts}" fill="{fill}" opacity="{opacity}"/>'


def _cube(
    gx: int,
    gy: int,
    cube,
    scene: ObliqueScene,
    touches: dict[str, int],
    max_touch: int,
    *,
    roof: bool,
    colors: _Colors = CATEGORY_COLORS,
) -> str:
    """Draw one file-cube: front/right side walls, plus a roof on top."""
    top_color, left_color, right_color = colors[categorize(cube.file.path)]
    touch = touches.get(cube.file.path, 0)

    p = scene.params
    ox, oy = scene.offset_x, scene.offset_y
    bl = _ground(gx, gy, p)
    br = _ground(gx + 1, gy, p)
    fl = _ground(gx, gy + 1, p)
    fr = _ground(gx + 1, gy + 1, p)
    bot, top_h = cube.bottom * p.height_scale, cube.top * p.height_scale

    def at(p: tuple[float, float], h: float) -> tuple[float, float]:
        """Screen point of ground corner *p* raised to height *h* (with offset)."""
        return p[0] + ox, p[1] + oy - h

    stroke = 'stroke="#0a0f1e" stroke-width="0.4" stroke-opacity="0.45"'
    parts = [
        _poly(
            [at(fl, bot), at(fr, bot), at(fr, top_h), at(fl, top_h)],
            _scale(left_color, _FACE_DIM),
            stroke,
        ),
        _poly(
            [at(fr, bot), at(br, bot), at(br, top_h), at(fr, top_h)],
            _scale(right_color, _FACE_DIM),
            stroke,
        ),
    ]
    if roof:
        top = [at(bl, top_h), at(br, top_h), at(fr, top_h), at(fl, top_h)]
        parts.append(
            _poly(
                top,
                _scale(top_color, _FACE_DIM),
                'stroke="#0a0f1e" stroke-width="0.4" stroke-opacity="0.4"',
            )
        )
        win_fill, win_opacity = window_light(touch, max_touch)
        parts.append(_roof_window(top, fill=win_fill, opacity=win_opacity))
    return "".join(parts)
