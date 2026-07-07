"""The shared scene core: directory-treemap packing + the isometric ``VoxelScene``.

Not a style module: every registered style builds on the machinery here
(``_pack_node``, ``_PackConfig``, ``VoxelScene``, ``Tower``). Upstream this
lives inside the ``voxel`` style module; that render is not in this port.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from repoglyph.geometry import (
    _CONTENT_PAD,
    _ROOF_MARGIN,
    TILE_H,
    TILE_W,
    _build_tree,
    _TreeNode,
    iso,
)
from repoglyph.models import SourceFile

__all__ = [
    "VoxelScene",
    "Tower",
    "build_voxel",
]

#: Clockwise view rotation (radians) for the ``voxel-plot`` ground plane.
_VIEW_ROT_PLOT = math.radians(26.0)

#: Tallest a single file-cube can be, so one giant file can't dwarf the tower.
_CUBE_CAP = 46.0
#: Shortest a file-cube can be, so tiny files still read as a distinct block.
_MIN_CUBE = 3.0
#: Tallest a directory-tower can be; over this the cubes compress to fit.
_TOWER_CAP = 340.0


@dataclass(slots=True)
class _Cube:
    """One file as a stacked slab, ``bottom``/``top`` measured up from ground."""

    file: SourceFile
    bottom: float
    top: float


@dataclass(slots=True)
class Tower:
    """One directory as an isometric tower of file-cubes on the grid."""

    grid_x: int
    grid_y: int
    district: str
    cubes: list[_Cube]
    height: float


def _cube_height(size: int) -> float:
    """Vertical slice for a file of *size* bytes, floored and capped."""
    return min(_CUBE_CAP, max(_MIN_CUBE, 1.2 * size ** (1 / 3)))


def _make_tower(grid_x: int, grid_y: int, district: str, files: tuple[SourceFile, ...]) -> Tower:
    """Stack *files* into a tower, biggest at the bottom, compressed to the cap."""
    members = sorted(files, key=lambda file: (-file.size, file.path))
    heights = [_cube_height(file.size) for file in members]
    total = sum(heights)
    if total > _TOWER_CAP:
        squeeze = _TOWER_CAP / total
        heights = [height * squeeze for height in heights]
        total = _TOWER_CAP

    cubes: list[_Cube] = []
    cursor = 0.0
    for file, height in zip(members, heights, strict=True):
        cubes.append(_Cube(file, cursor, cursor + height))
        cursor += height
    return Tower(grid_x, grid_y, district, cubes, total)


#: A grid cell holding a directory-tower: (grid_x, grid_y, path, files).
_Cell = tuple[int, int, str, tuple[SourceFile, ...]]


@dataclass(slots=True)
class _PackBlock:
    """A packed rectangle of tower cells, positioned relative to its origin."""

    width: int
    height: int
    cells: list[_Cell]

    @property
    def area(self) -> int:
        return self.width * self.height


#: Suffix marking a directory's own-file cluster in pack hints, so its key never
#: collides with a real sub-directory path under the same parent.
_FILE_KEY = "\x00files"


@dataclass(slots=True)
class _PackHints:
    """HEAD-derived layout hints for de-flickered timelapses."""

    area: dict[str, float]
    width: dict[str, int]
    dims: dict[str, tuple[int, int]]
    offset: dict[str, tuple[int, int]]


def _target_w(blocks: list[_PackBlock], aspect: float) -> int:
    """The shelf wrap width for *blocks*: the widest block, or a sqrt(area) grid."""
    total_area = sum(block.area for block in blocks)
    return max(
        max(block.width for block in blocks),
        math.ceil(math.sqrt(total_area * aspect)),
    )


def _arrange(
    keyed: list[tuple[str, _PackBlock]],
    gap: int,
    aspect: float = 1.0,
    target_w: int | None = None,
    hints: _PackHints | None = None,
    record_offset: dict[str, tuple[int, int]] | None = None,
) -> _PackBlock:
    """Lay *keyed* ``(key, block)`` pairs into one wide-ish super-block."""
    blocks = [block for _, block in keyed]
    if target_w is None:
        target_w = _target_w(blocks, aspect)

    cells: list[_Cell] = []
    max_x = max_y = 0

    def emit(block: _PackBlock, ox: int, oy: int) -> None:
        nonlocal max_x, max_y
        for gx, gy, path, files in block.cells:
            cells.append((ox + gx, oy + gy, path, files))
        max_x = max(max_x, ox + block.width)
        max_y = max(max_y, oy + block.height)

    if hints is not None:
        transient: list[_PackBlock] = []
        for key, block in keyed:
            off = hints.offset.get(key)
            if off is None:
                transient.append(block)
            else:
                emit(block, off[0], off[1])
        cursor_x = 0
        cursor_y = max_y + gap if max_y else 0
        shelf_h = 0
        for block in transient:
            if cursor_x > 0 and cursor_x + block.width > target_w:
                cursor_y += shelf_h + gap
                cursor_x = 0
                shelf_h = 0
            emit(block, cursor_x, cursor_y)
            cursor_x += block.width + gap
            shelf_h = max(shelf_h, block.height)
        return _PackBlock(max_x, max_y, cells)

    cursor_x = cursor_y = shelf_h = 0
    for key, block in keyed:
        if cursor_x > 0 and cursor_x + block.width > target_w:
            cursor_y += shelf_h + gap
            cursor_x = 0
            shelf_h = 0
        if record_offset is not None:
            record_offset[key] = (cursor_x, cursor_y)
        emit(block, cursor_x, cursor_y)
        cursor_x += block.width + gap
        shelf_h = max(shelf_h, block.height)
    return _PackBlock(max_x, max_y, cells)


def _pad_block(block: _PackBlock, key: str, hints: _PackHints | None) -> _PackBlock:
    """Pad *block* up to its HEAD ``(width, height)`` (cells untouched), so a
    not-yet-grown block still fills its final slot. No-op without hints, for a
    transient block, or once the block has reached its HEAD size."""
    if hints is None:
        return block
    dims = hints.dims.get(key)
    if dims is None:
        return block
    width, height = dims
    if block.width >= width and block.height >= height:
        return block
    return _PackBlock(max(block.width, width), max(block.height, height), block.cells)


@dataclass(slots=True, frozen=True)
class _PackConfig:
    """Knobs that distinguish the voxel variants (renderer is shared)."""

    streets: tuple[int, ...] = (1, 0, 0)
    max_depth: int | None = None
    plot: bool = False
    root_files_last: bool = False


#: Baseline pack (single stacked tower per directory); default for VoxelScene.build.
_BASE = _PackConfig()
#: Oblique variant configurations.
_OBLIQUE = _PackConfig(streets=(1, 0, 0), plot=True, root_files_last=True)


def _street_for(streets: tuple[int, ...], depth: int) -> int:
    """Lane width between sibling blocks at *depth*, clamped to the table."""
    return streets[min(depth, len(streets) - 1)]


def _subtree_files(node: _TreeNode) -> list[SourceFile]:
    """Every file in *node* and all its descendants (for depth flattening)."""
    files = list(node.files)
    for sub in node.dirs.values():
        files += _subtree_files(sub)
    return files


def _file_cells(path: str, files: list[SourceFile], *, plot: bool) -> _PackBlock:
    """A directory's own files as grid cells."""
    if not plot:
        return _PackBlock(1, 1, [(0, 0, path or ".root", tuple(files))])
    members = sorted(files, key=lambda file: (-file.size, file.path))
    cols = max(1, math.ceil(math.sqrt(len(members))))
    rows = math.ceil(len(members) / cols)
    cells: list[_Cell] = [
        (i % cols, i // cols, path or ".root", (file,)) for i, file in enumerate(members)
    ]
    return _PackBlock(cols, rows, cells)


def _pack_node(
    node: _TreeNode,
    path: str,
    depth: int,
    cfg: _PackConfig,
    aspect: float = 1.0,
    hints: _PackHints | None = None,
    record: _PackHints | None = None,
) -> _PackBlock:
    """Pack a directory node: sub-directory blocks and files."""
    if cfg.max_depth is not None and depth >= cfg.max_depth:
        files = _subtree_files(node)
        block = _file_cells(path, files, plot=cfg.plot) if files else _PackBlock(0, 0, [])
        if record is not None and block.cells:
            record.area[path] = block.area
            record.dims[path] = (block.width, block.height)
        return _pad_block(block, path, hints)

    def file_sort_key(block: _PackBlock) -> tuple[float, str]:
        # Loose root files trail every district when ``root_files_last`` (inf
        # sorts last); otherwise sort by area like any block.
        if cfg.root_files_last and depth == 0:
            return (float("inf"), "")
        order = hints.area.get(file_key, block.area) if hints else block.area
        return (-order, "")

    file_key = path + _FILE_KEY
    blocks: list[tuple[tuple[float, str], str, _PackBlock]] = []
    for name, sub in node.dirs.items():
        child_path = f"{path}/{name}" if path else name
        sub_block = _pack_node(sub, child_path, depth + 1, cfg, aspect, hints, record)
        if sub_block.cells:
            order = hints.area.get(child_path, sub_block.area) if hints else sub_block.area
            blocks.append(((-order, name), child_path, sub_block))
    if node.files:
        cluster = _file_cells(path, list(node.files), plot=cfg.plot)
        if record is not None:
            record.area[file_key] = cluster.area
            record.dims[file_key] = (cluster.width, cluster.height)
        cluster = _pad_block(cluster, file_key, hints)
        blocks.append((file_sort_key(cluster), file_key, cluster))

    if not blocks:
        return _PackBlock(0, 0, [])
    blocks.sort(key=lambda item: item[0])
    ordered = [(key, block) for _, key, block in blocks]
    target_w = hints.width.get(path) if hints else None
    arranged = _arrange(
        ordered,
        gap=_street_for(cfg.streets, depth),
        aspect=aspect,
        target_w=target_w,
        hints=hints,
        record_offset=record.offset if record is not None else None,
    )
    if record is not None:
        record.area[path] = arranged.area
        record.width[path] = _target_w([block for _, block in ordered], aspect)
        record.dims[path] = (arranged.width, arranged.height)
    return _pad_block(arranged, path, hints)


@dataclass(slots=True)
class VoxelScene:
    """The voxel city scene in its content coordinates."""

    towers: list[Tower]
    offset_x: float
    offset_y: float
    content_width: float
    content_height: float
    view_rot: float = 0.0

    @classmethod
    def build(
        cls, files: list[SourceFile], cfg: _PackConfig = _BASE, view_rot: float = 0.0
    ) -> VoxelScene:
        """Pack files into directory-towers and size the content box."""
        block = _pack_node(_build_tree(files), "", 0, cfg)
        towers = [
            _make_tower(grid_x, grid_y, district, members)
            for grid_x, grid_y, district, members in block.cells
        ]

        xs: list[float] = []
        ys: list[float] = []
        if view_rot:
            # Rotated: bound by the turned parallelogram's actual corners (ground
            # and extruded roof), or a turned city would clip.
            corners = _footprint(view_rot)
            for tower in towers:
                x, y = iso(tower.grid_x, tower.grid_y, view_rot)
                for dx, dy in corners:
                    xs.append(x + dx)
                    ys += [y + dy, y + dy - tower.height - _ROOF_MARGIN]
        else:
            for tower in towers:
                x, y = iso(tower.grid_x, tower.grid_y, view_rot)
                xs += [x - TILE_W, x + TILE_W]
                ys += [y - tower.height - _ROOF_MARGIN, y + TILE_H]

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
            view_rot=view_rot,
        )


def build_voxel(
    files: list[SourceFile], *, streets: int = 1, depth_cap: int | None = None
) -> VoxelScene:
    """Build an isometric ``VoxelScene`` (used by tests and district grouping)."""
    cfg = _PackConfig(streets=(streets, streets, 0), max_depth=depth_cap, plot=True)
    return VoxelScene.build(files, cfg, view_rot=_VIEW_ROT_PLOT)


#: Faces are dimmed a touch toward night so the lit windows read against them
#: (kept: ``oblique``/``highrise`` import ``_FACE_DIM`` and ``_scale``).
_FACE_DIM = 0.85
#: Half-extent of the roof window diamond, as a fraction of the top face
#: (kept: ``oblique`` imports ``_ROOF_WIN``).
_ROOF_WIN = 0.5


def _scale(color: str, factor: float) -> str:
    """Scale a ``#rrggbb`` color's brightness by *factor*, clamped to [0, 255]."""
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

    def channel(value: int) -> int:
        return max(0, min(255, round(value * factor)))

    return f"#{channel(r):02x}{channel(g):02x}{channel(b):02x}"


def _footprint(view_rot: float) -> tuple[tuple[float, float], ...]:
    """Screen offsets of a unit cell's four ground corners from its centre."""
    ex = iso(1, 0, view_rot)
    ey = iso(0, 1, view_rot)
    return (
        (-(ex[0] + ey[0]) / 2, -(ex[1] + ey[1]) / 2),
        ((ex[0] - ey[0]) / 2, (ex[1] - ey[1]) / 2),
        ((ex[0] + ey[0]) / 2, (ex[1] + ey[1]) / 2),
        ((-ex[0] + ey[0]) / 2, (-ex[1] + ey[1]) / 2),
    )
