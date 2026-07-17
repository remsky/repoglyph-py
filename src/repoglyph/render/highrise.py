"""The "highrise" style: one building per neighbourhood, floors are subdirs.

Each frontier directory collapses into a single tower. A floor is one immediate
sub-directory (its files, and those nested below it, count as that floor's rooms);
a windowed room is a file, lit when it was touched in the recent commit window.
So a big repository stays a readable skyline of a dozen labelled towers rather
than a field of one-cell buildings.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from repoglyph.geometry import _CONTENT_PAD, _ROOF_MARGIN, BannerLayout, iso
from repoglyph.models import SourceFile
from repoglyph.palette import CATEGORY_COLORS, Category, categorize
from repoglyph.palettes import DARK_CHROME, Chrome
from repoglyph.render.districts import _LABEL_SIZE, Projection, _overlaps
from repoglyph.render.lighting import window_light
from repoglyph.render.scene import _Cube, _scale

__all__ = ["HighriseScene", "build_highrise", "draw_floor_labels", "render_highrise"]

type _Colors = dict[Category, tuple[str, str, str]]

#: Building footprint half-extents in screen px (wider than a single iso tile).
_HALF_W = 44.0
_HALF_D = 25.0
#: Base grid spacing between neighbouring towers, in grid cells (at ``--streets 1``).
_STEP_BASE = 3
#: Floor sizing: window columns per face, px per window row, and the row cap.
_COLS = 3
_ROW_PX = 14.0
_ROWS_CAP = 5
#: A single building is compressed to fit under this total height.
_TOWER_CAP = 300.0
#: Faces are dimmed toward night so the lit rooms read against them.
_FACE_DIM = 0.82


@dataclass(slots=True)
class Floor:
    """One sub-directory of a neighbourhood: its rooms (files) stacked as a band."""

    name: str
    files: list[SourceFile]
    category: Category
    rows: int
    bottom: float
    top: float


@dataclass(slots=True)
class Building:
    """A neighbourhood collapsed to one tower; ``cubes`` mirrors files for stats."""

    grid_x: int
    grid_y: int
    district: str
    height: float
    floors: list[Floor]
    cubes: list[_Cube] = field(default_factory=list)


@dataclass(slots=True)
class HighriseScene:
    """The highrise scene: towers (buildings) in local content coordinates."""

    towers: list[Building]
    offset_x: float
    offset_y: float
    content_width: float
    content_height: float
    view_rot: float = 0.0


def _building_frontier(files: list[SourceFile], cap: int) -> set[str]:
    """The set of directories that become their own building.

    *cap* is the detail budget: starting from the top-level dirs, the densest
    splittable dir is peeled into its immediate sub-dirs (which each become
    buildings) until the frontier reaches the cap. A split dir stays in the
    frontier as the lobby for its own loose files. So low detail = a few tall
    towers (deep dirs collapse into floors), high detail = more, shorter towers.
    """
    count: dict[str, int] = {}
    children: dict[str, set[str]] = {}
    for file in files:
        segs = file.path.split("/")
        for i in range(1, len(segs)):
            dir_path = "/".join(segs[:i])
            count[dir_path] = count.get(dir_path, 0) + 1
            if i >= 2:
                children.setdefault("/".join(segs[: i - 1]), set()).add(dir_path)

    frontier = {d for d in count if "/" not in d}
    opened: set[str] = set()
    while len(frontier) < cap:
        cands = sorted(
            (d for d in frontier if d in children and d not in opened),
            key=lambda d: (-count[d], d),
        )
        if not cands:
            break
        target = cands[0]
        opened.add(target)
        frontier |= children[target]
    return frontier


def _assign_buildings(files: list[SourceFile], frontier: set[str]) -> dict[str, list[SourceFile]]:
    """Partition files to buildings: each file joins the deepest frontier dir that
    prefixes it (root files -> the ``.root`` building)."""
    by_building: dict[str, list[SourceFile]] = {}
    for file in files:
        segs = file.path.split("/")
        best = ".root"
        for i in range(1, len(segs)):
            dir_path = "/".join(segs[:i])
            if dir_path in frontier:
                best = dir_path
        by_building.setdefault(best, []).append(file)
    return by_building


def _place_buildings(buildings: list[Building], step: int) -> None:
    """Grouped placement: a directory's promoted sub-buildings stay in one contiguous
    block instead of scattering by size rank.

    Each top-level family becomes a rectangular cluster (members in path order);
    families are shelf-packed largest-first. *step* is the per-slot grid spacing.
    """
    families: dict[str, list[Building]] = {}
    for building in buildings:
        top = ".root" if building.district == ".root" else building.district.split("/")[0]
        families.setdefault(top, []).append(building)

    ranked: list[tuple[str, list[Building], int, int, int]] = []
    for key, members in families.items():
        members.sort(key=lambda b: b.district)
        cols = max(1, math.ceil(math.sqrt(len(members))))
        rows = math.ceil(len(members) / cols)
        total = sum(len(member.cubes) for member in members)
        ranked.append((key, members, cols, rows, total))
    ranked.sort(key=lambda fam: (-fam[4], fam[0]))

    target_w = max(1, math.ceil(math.sqrt(len(buildings))))
    cursor_x = cursor_y = shelf_h = 0
    for _key, members, cols, rows, _total in ranked:
        if cursor_x > 0 and cursor_x + cols > target_w:
            cursor_y += shelf_h
            cursor_x = 0
            shelf_h = 0
        for i, building in enumerate(members):
            building.grid_x = (cursor_x + i % cols) * step
            building.grid_y = (cursor_y + i // cols) * step
        cursor_x += cols
        shelf_h = max(shelf_h, rows)


def _floor_of(path: str, district: str) -> str:
    """The immediate sub-directory of *district* that owns *path* (or its lobby)."""
    rest = path[len(district) + 1 :] if district != ".root" else path
    head, sep, _ = rest.partition("/")
    return head if sep else ""


def _dominant(files: list[SourceFile]) -> Category:
    """The most common file category among *files* (name tiebreak)."""
    counts = Counter(categorize(file.path) for file in files)
    return min(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]


def _make_building(district: str, files: list[SourceFile]) -> Building:
    """Split a building's files into floors and size the tower (placed later)."""
    by_floor: dict[str, list[SourceFile]] = {}
    for file in files:
        by_floor.setdefault(_floor_of(file.path, district), []).append(file)

    # Lobby (own files, key "") sinks to the bottom; sub-dirs stack largest-first.
    ordered = sorted(by_floor.items(), key=lambda kv: (kv[0] != "", -len(kv[1]), kv[0]))
    floors: list[Floor] = []
    cursor = 0.0
    for name, members in ordered:
        rows = max(1, min(_ROWS_CAP, math.ceil(len(members) / _COLS)))
        height = rows * _ROW_PX
        floors.append(Floor(name, members, _dominant(members), rows, cursor, cursor + height))
        cursor += height

    if cursor > _TOWER_CAP:
        squeeze = _TOWER_CAP / cursor
        for floor in floors:
            floor.bottom *= squeeze
            floor.top *= squeeze
        cursor = _TOWER_CAP

    return Building(
        0,
        0,
        district,
        cursor,
        floors,
        cubes=[_Cube(file, 0.0, 0.0) for file in files],
    )


def build_highrise(files: list[SourceFile], *, streets: int = 1, detail: int = 14) -> HighriseScene:
    """Build the highrise scene: one tower per building in the *detail*-bounded
    frontier, grouped so a directory's sub-buildings cluster together.

    *detail* sets how deep the tree unfolds into separate towers (see
    :func:`_building_frontier`). *streets* widens the avenues between towers
    (``--streets``); the default ``1`` keeps the base spacing, higher values
    spread the skyline.
    """
    step = max(1, _STEP_BASE + streets - 1)
    frontier = _building_frontier(files, detail)
    buildings = [
        _make_building(district, members)
        for district, members in _assign_buildings(files, frontier).items()
    ]
    _place_buildings(buildings, step)

    xs: list[float] = []
    ys: list[float] = []
    for building in buildings:
        x, y = iso(building.grid_x, building.grid_y)
        xs += [x - _HALF_W, x + _HALF_W]
        ys += [y - building.height - _ROOF_MARGIN, y + _HALF_D]

    if xs:
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
    else:
        min_x = max_x = min_y = max_y = 0.0

    return HighriseScene(
        towers=buildings,
        offset_x=_CONTENT_PAD - min_x,
        offset_y=_CONTENT_PAD - min_y,
        content_width=(max_x - min_x) + 2 * _CONTENT_PAD,
        content_height=(max_y - min_y) + 2 * _CONTENT_PAD,
    )


def _band(ox: float, oy: float, fx: float, fy: float, b: float, t: float) -> str:
    """A wall quad along ground edge outer->front, extruded between heights b..t."""
    return (
        f"{ox:.1f},{oy - t:.1f} {fx:.1f},{fy - t:.1f} {fx:.1f},{fy - b:.1f} {ox:.1f},{oy - b:.1f}"
    )


def _rooms(
    ox: float,
    oy: float,
    fx: float,
    fy: float,
    floor: Floor,
    touches: dict[str, int],
    max_touch: int,
) -> str:
    """Draw one window per file across the floor band (lit when recently touched)."""
    ex, ey = fx - ox, fy - oy
    du = 0.32 / _COLS
    dv = 0.30 * _ROW_PX
    span = floor.top - floor.bottom
    members = sorted(floor.files, key=lambda file: (-file.size, file.path))
    cells: list[str] = []
    for index, file in enumerate(members[: _COLS * floor.rows]):
        col = index % _COLS
        row = index // _COLS
        u = (col + 0.5) / _COLS
        h = floor.bottom + (row + 0.5) / floor.rows * span
        cx, cy = ox + u * ex, oy + u * ey - h
        touch = touches.get(file.path, 0)
        fill, opacity = window_light(touch, max_touch)
        points = " ".join(
            f"{cx + su * du * ex:.1f},{cy + su * du * ey + sv * dv:.1f}"
            for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))
        )
        cells.append(f'<polygon points="{points}" fill="{fill}" opacity="{opacity}"/>')
    return "".join(cells)


def _building_svg(
    building: Building,
    scene: HighriseScene,
    touches: dict[str, int],
    max_touch: int,
    colors: _Colors,
) -> str:
    """Draw one neighbourhood tower: stacked, windowed, per-subdir coloured floors."""
    cx = iso(building.grid_x, building.grid_y)[0] + scene.offset_x
    cy = iso(building.grid_x, building.grid_y)[1] + scene.offset_y
    left = (cx - _HALF_W, cy)
    right = (cx + _HALF_W, cy)
    front = (cx, cy + _HALF_D)
    stroke = 'stroke="#0a0f1e" stroke-width="0.4" stroke-opacity="0.45"'

    parts: list[str] = []
    for floor in building.floors:
        _, lc, rc = colors[floor.category]
        parts.append(
            f'<polygon points="{_band(*left, *front, floor.bottom, floor.top)}" '
            f'fill="{_scale(lc, _FACE_DIM)}" {stroke}/>'
        )
        parts.append(
            f'<polygon points="{_band(*right, *front, floor.bottom, floor.top)}" '
            f'fill="{_scale(rc, _FACE_DIM)}" {stroke}/>'
        )
        parts.append(_rooms(*left, *front, floor, touches, max_touch))
        parts.append(_rooms(*right, *front, floor, touches, max_touch))

    top_color = colors[building.floors[-1].category][0] if building.floors else "#888"
    h = building.height
    roof = (
        f"{cx:.1f},{cy - _HALF_D - h:.1f} {cx + _HALF_W:.1f},{cy - h:.1f} "
        f"{cx:.1f},{cy + _HALF_D - h:.1f} {cx - _HALF_W:.1f},{cy - h:.1f}"
    )
    parts.append(f'<polygon points="{roof}" fill="{_scale(top_color, _FACE_DIM)}" {stroke}/>')
    return "".join(parts)


def render_highrise(
    scene: HighriseScene,
    touches: dict[str, int],
    max_touch: int,
    *,
    colors: _Colors = CATEGORY_COLORS,
    chrome: Chrome = DARK_CHROME,
) -> str:
    """Render every neighbourhood tower, painter-sorted back-to-front."""
    ordered = sorted(scene.towers, key=lambda b: iso(b.grid_x, b.grid_y)[::-1])
    body = "".join(_building_svg(b, scene, touches, max_touch, colors) for b in ordered)
    return f"<g>{body}</g>"


#: Clearance in screen px between a tower's right corner and its floor label.
_FLOOR_LABEL_PAD = 5.0


def draw_floor_labels(
    scene: HighriseScene,
    banner: BannerLayout,
    proj: Projection,
    label_ink: str | None = None,
    label_halo: str | None = None,
    ts: float = 1.0,
) -> str:
    """Name each tower's floors (its immediate sub-directories) in the avenue to
    the building's right, at the floor's mid-height.

    The tower's own district label (drawn by the leaf cut) names the
    neighbourhood; this reveals what's stacked inside it. Floors are placed
    largest-first and the collision dodge drops the rest, so this complements
    the ``detail`` slider: a tall tower's floors are named here, and turning
    detail up promotes those same dirs into their own towers. The lobby (a
    tower's own loose files, floor ``""``) is skipped; it has no name to show.
    """
    size = _LABEL_SIZE * ts
    box_h = 1.3 * size

    entries = [
        (tower, floor) for tower in scene.towers for floor in tower.floors if floor.name != ""
    ]
    entries.sort(key=lambda e: (-len(e[1].files), e[1].name, e[0].district))

    placed: list[tuple[float, float, float, float]] = []
    out: list[str] = []
    for tower, floor in entries:
        name = floor.name
        gx, gy = proj.ground(tower.grid_x, tower.grid_y)
        mid = (floor.bottom + floor.top) / 2
        corner_x = gx + _HALF_W + scene.offset_x
        corner_y = gy - mid * proj.height_scale + scene.offset_y

        text_w = 0.62 * size * len(name) + 4.0 * ts
        px0 = min(
            banner.content_tx + corner_x * banner.scale + _FLOOR_LABEL_PAD,
            banner.width - 6 - text_w,
        )
        py = banner.content_ty + corner_y * banner.scale

        box = (px0, py - box_h, px0 + text_w, py + box_h * 0.25)
        if any(_overlaps(box, other) for other in placed):
            continue
        placed.append(box)
        out.append(proj.emit_label(px0, py, name, size, label_ink, label_halo))
    return "".join(out)
