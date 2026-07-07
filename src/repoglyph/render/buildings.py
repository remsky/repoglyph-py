"""Render the skyline: one isometric building per file, with lit windows."""

from __future__ import annotations

from repoglyph.geometry import (
    TILE_H,
    TILE_W,
    PlacedBuilding,
    Scene,
    building_height,
    iso,
)
from repoglyph.hashing import stable_unit
from repoglyph.palette import CATEGORY_COLORS, Category, categorize
from repoglyph.render.lighting import window_light

__all__ = ["render_buildings"]

#: Roof-beacon diamond inset toward the roof centre; matches oblique's roof_light factor.
_ROOF_WIN = 0.5

type _Colors = dict[Category, tuple[str, str, str]]


def render_buildings(
    scene: Scene,
    touches: dict[str, int],
    max_touch: int,
    *,
    colors: _Colors = CATEGORY_COLORS,
) -> str:
    """Render every placed building, painter-sorted back-to-front.

    A touched file also lights a diamond on its roof; side-face windows get
    occluded by neighbours in a tight pack, so the roof beacon is the
    near-always-visible "is this file alive" cue, mirroring oblique's
    ``roof_light``.
    """
    ordered = sorted(
        scene.buildings,
        key=lambda b: iso(b.grid_x, b.grid_y)[::-1],
    )
    body = "".join(_building(building, scene, touches, max_touch, colors) for building in ordered)
    return f"<g>{body}</g>"


def _roof_beacon(x: float, roof_y: float, touch: int, max_touch: int) -> str:
    """A lit diamond inset on the roof face, the touched-file beacon."""
    fill, opacity = window_light(touch, max_touch)
    pts = (
        f"{x:.1f},{roof_y - TILE_H * _ROOF_WIN:.1f} "
        f"{x + TILE_W * _ROOF_WIN:.1f},{roof_y:.1f} "
        f"{x:.1f},{roof_y + TILE_H * _ROOF_WIN:.1f} "
        f"{x - TILE_W * _ROOF_WIN:.1f},{roof_y:.1f}"
    )
    return f'<polygon points="{pts}" fill="{fill}" opacity="{opacity}" stroke="none"/>'


def _building(
    building: PlacedBuilding,
    scene: Scene,
    touches: dict[str, int],
    max_touch: int,
    colors: _Colors,
) -> str:
    file = building.file
    x, y = iso(building.grid_x, building.grid_y)
    x += scene.offset_x
    y += scene.offset_y
    height = building_height(file.size)
    top_color, left_color, right_color = colors[categorize(file.path)]
    touch = touches.get(file.path, 0)

    roof_x, roof_y = x, y - height
    top_face = (
        f"{roof_x},{roof_y - TILE_H} {roof_x + TILE_W},{roof_y} "
        f"{roof_x},{roof_y + TILE_H} {roof_x - TILE_W},{roof_y}"
    )
    left_face = (
        f"{roof_x - TILE_W},{roof_y} {roof_x},{roof_y + TILE_H} {x},{y + TILE_H} {x - TILE_W},{y}"
    )
    right_face = (
        f"{roof_x + TILE_W},{roof_y} {roof_x},{roof_y + TILE_H} {x},{y + TILE_H} {x + TILE_W},{y}"
    )

    parts: list[str] = []
    parts.append(f'<polygon points="{left_face}" fill="{left_color}"/>')
    parts.append(f'<polygon points="{right_face}" fill="{right_color}"/>')
    parts.append(
        f'<polygon points="{top_face}" fill="{top_color}" '
        'stroke="#0a0f1e" stroke-width="0.4" stroke-opacity="0.4"/>'
    )
    parts.append(_windows(x, y, height, touch, max_touch, face="L"))
    parts.append(_windows(x, y, height, touch, max_touch, face="R"))
    # Roof beacon last so it sits on top of the roof face; only for touched files.
    if touch > 0:
        parts.append(_roof_beacon(x, roof_y, touch, max_touch))
    return "".join(parts)


def _windows(
    x: float,
    y: float,
    height: float,
    touch: int,
    max_touch: int,
    *,
    face: str,
) -> str:
    """Render the window grid on one face; lit window colour scales with touches."""
    rows = min(8, max(1, int(height / 15)))
    cols = 2
    lit_fraction = 0.05 if touch == 0 else 0.45
    lit_color, lit_opacity = window_light(touch, max_touch)

    cells: list[str] = []
    for row in range(rows):
        for col in range(cols):
            u = (col + 0.5) / cols
            v = (row + 0.55) / rows
            du = 0.34 / cols
            dv = 0.30 / rows
            points: list[str] = []
            for uu, vv in [
                (u - du, v - dv),
                (u + du, v - dv),
                (u + du, v + dv),
                (u - du, v + dv),
            ]:
                if face == "L":  # noqa: SIM108 - the two mirrored branches read clearer apart
                    px = x - TILE_W + uu * TILE_W
                else:
                    px = x + TILE_W - uu * TILE_W
                py = (y - height) + uu * TILE_H + vv * height
                points.append(f"{px:.1f},{py:.1f}")
            lit = stable_unit(x, y, face, row, col) < lit_fraction
            fill = lit_color if lit else "#0b1430"
            opacity = lit_opacity if lit else 0.6
            cells.append(
                f'<polygon points="{" ".join(points)}" fill="{fill}" opacity="{opacity}"/>'
            )
    return "".join(cells)
