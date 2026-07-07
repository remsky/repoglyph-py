"""Isometric projection, the shared directory tree, and banner layout."""

from __future__ import annotations

import math
from dataclasses import dataclass

from repoglyph.models import SourceFile

__all__ = [
    "TILE_W",
    "TILE_H",
    "HEIGHT_CAP",
    "BANNER_WIDTH",
    "BANNER_HEIGHT",
    "HUD_PAD",
    "PANEL_WIDTH",
    "LEGEND_SPAN",
    "LEGEND_STRIP",
    "STAGE_GAP",
    "MAX_UPSCALE",
    "PANEL_STATS_HEIGHT",
    "CROWD_PANEL_GAP",
    "CROWD_HEAD_RADIUS",
    "CROWD_COL_SPACING",
    "CROWD_ROW_SPACING",
    "BannerLayout",
    "PlacedBuilding",
    "Scene",
    "iso",
    "building_height",
    "fit_banner",
]

# --- isometric grid -------------------------------------------------------
# Grid cell width and height (defines the isometric viewing angle).
TILE_W = 28
TILE_H = 16
HEIGHT_CAP = 205

# --- ground-plane rotation -------------------------------------------------
# Clockwise rotation angle for the ground grid in screen space.
_VIEW_ROT_DEG = 0.0
_VIEW_ROT = math.radians(_VIEW_ROT_DEG)
_ROT_COS = math.cos(_VIEW_ROT)
_ROT_SIN = math.sin(_VIEW_ROT)

# --- banner canvas (fixed-size output) ------------------------------------
# Canvas dimensions and layout settings; HUD is fixed, city content scales to fit.
BANNER_WIDTH = 1280
BANNER_HEIGHT = 480
#: Outer margin around the whole canvas.
HUD_PAD = 24
#: Left band reserved for the title + stats fingerprint (canvas px).
PANEL_WIDTH = 300
#: Width of the horizontal colour legend at the bottom-right (canvas px).
LEGEND_SPAN = 380
#: Bottom strip reserved under the stage for that legend, so the city floor
#: never collides with the swatches.
LEGEND_STRIP = 30
#: Gap between a HUD band and the city stage.
STAGE_GAP = 16
#: Cap on how far a small repo's content is enlarged to fill the stage.
MAX_UPSCALE = 3.0
#: Multiplier on the fit scale.
STAGE_ZOOM = 1.0
#: Vertical space (px below the top pad) the title + stats text occupies; the
#: crowd stands below it.
PANEL_STATS_HEIGHT = 196
#: Gap between the stats text and the crowd standing beneath it.
CROWD_PANEL_GAP = 14
#: Minimum canvas height in `--full` mode, so the HUD always fits.
_MIN_FULL_HEIGHT = 320
#: Breathing room (content units) around the city inside its own bbox.
_CONTENT_PAD = 12
#: Headroom above a building's roof for the roof diamond + glow halo, when
#: measuring the content bbox (so the box hugs the actual skyline height).
_ROOF_MARGIN = 26

# --- crowd layout ---------------------------------------------------------
# Figure metrics for the contributor crowd below the stats panel.
CROWD_HEAD_RADIUS = 16
CROWD_COL_SPACING = 39
CROWD_ROW_SPACING = 30


def iso(grid_x: float, grid_y: float, rot: float = _VIEW_ROT) -> tuple[float, float]:
    """Project grid coordinates to isometric screen coordinates with rotation."""
    x = (grid_x - grid_y) * TILE_W
    y = (grid_x + grid_y) * TILE_H
    cos_r, sin_r = (_ROT_COS, _ROT_SIN) if rot == _VIEW_ROT else (math.cos(rot), math.sin(rot))
    return x * cos_r - y * sin_r, x * sin_r + y * cos_r


def building_height(size_bytes: int) -> float:
    """Map a file's byte size to a building height, capped at ``HEIGHT_CAP``."""
    return min(HEIGHT_CAP, 8 + 7.2 * math.sqrt(max(size_bytes, 1)) ** 0.5 * 1.6)


@dataclass(slots=True)
class PlacedBuilding:
    """A file assigned a position on the isometric grid."""

    file: SourceFile
    grid_x: int
    grid_y: int


@dataclass(slots=True)
class _TreeNode:
    """A directory in the repo tree: its sub-directories and its own files."""

    dirs: dict[str, _TreeNode]
    files: list[SourceFile]


def _build_tree(files: list[SourceFile]) -> _TreeNode:
    """Reconstruct the directory hierarchy from file paths."""
    root = _TreeNode(dirs={}, files=[])
    for file in files:
        *parents, _name = file.path.split("/")
        node = root
        for part in parents:
            node = node.dirs.setdefault(part, _TreeNode(dirs={}, files=[]))
        node.files.append(file)
    return root


@dataclass(slots=True)
class Scene:
    """The city layout in local content coordinates (scaled/shifted)."""

    buildings: list[PlacedBuilding]
    offset_x: float
    offset_y: float
    #: Bounding box of the city content in content units.
    content_width: float
    content_height: float


@dataclass(slots=True)
class BannerLayout:
    """Canvas size, scaling, and anchors for drawing the banner and HUD."""

    width: int
    height: int
    scale: float
    content_tx: float
    content_ty: float
    panel_x: float
    legend_x: float
    legend_y: float
    divider_x: float
    pad: float
    #: Canvas-pixel box (x, y, w, h) the crowd stands in, below the stats panel.
    crowd_x: float
    crowd_y: float
    crowd_w: float
    crowd_h: float


def fit_banner(
    scene: Scene,
    *,
    width: int = BANNER_WIDTH,
    height: int = BANNER_HEIGHT,
    full: bool = False,
) -> BannerLayout:
    """Scale and position the scene content box on the banner canvas."""
    pad, gap = HUD_PAD, STAGE_GAP
    content_w = max(scene.content_width, 1.0)
    content_h = max(scene.content_height, 1.0)

    if full:
        scale = 1.0
        width = int(pad + PANEL_WIDTH + gap + content_w + pad)
        height = int(max(_MIN_FULL_HEIGHT, pad + content_h + LEGEND_STRIP + pad))

    stage_x = pad + PANEL_WIDTH + gap
    stage_y = pad
    # Stage spans the full right band; the bottom strip clears the legend swatches.
    stage_w = max(width - pad - stage_x, 1.0)
    stage_h = max(height - pad - LEGEND_STRIP - stage_y, 1.0)

    if not full:
        scale = min(stage_w / content_w, stage_h / content_h, MAX_UPSCALE) * STAGE_ZOOM

    content_tx = stage_x + (stage_w - content_w * scale) / 2
    # Ground the city and crowd to the stage floor.
    content_ty = stage_y + (stage_h - content_h * scale)

    crowd_y = pad + PANEL_STATS_HEIGHT + CROWD_PANEL_GAP
    crowd_h = max(height - pad - crowd_y, 1.0)

    return BannerLayout(
        width=width,
        height=height,
        scale=scale,
        content_tx=content_tx,
        content_ty=content_ty,
        panel_x=pad,
        legend_x=width - pad - LEGEND_SPAN,
        legend_y=height - pad - 8,
        divider_x=pad + PANEL_WIDTH + gap / 2,
        pad=pad,
        crowd_x=pad,
        crowd_y=crowd_y,
        crowd_w=PANEL_WIDTH,
        crowd_h=crowd_h,
    )
