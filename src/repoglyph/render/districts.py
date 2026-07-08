"""District annotation: the cross-projection boxes, labels and gold pulse."""

from __future__ import annotations

import html
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from repoglyph.geometry import BannerLayout, iso
from repoglyph.render.oblique import ObliqueScene, _ground
from repoglyph.render.scene import Tower, VoxelScene
from repoglyph.render.svg import text

__all__ = [
    "DistrictConfig",
    "Projection",
    "iso_projection",
    "oblique_projection",
    "district_cut",
    "district_groups",
    "draw_boxes",
    "draw_labels",
    "draw_emphasis",
]

# Grouping axis: the district cut and tower-to-district grouping.

#: A directory holding more than this fraction of all files is a "container":
#: the adaptive cut descends into its children instead of labelling it whole.
_DISTRICT_SPLIT = 0.35
#: Max districts the balanced cut produces (a scale-free hard ceiling).
_DISTRICT_CAP = 14


class _HasTowers(Protocol):
    """Structural view of a scene the district helpers need: just its towers."""

    towers: list[Tower]


def _district_cut(
    scene: _HasTowers, threshold: float, districts: frozenset[str] | None = None
) -> set[str]:
    """Pick the directory paths that read as meaningful neighbourhoods (adaptive cut)."""
    if districts is not None:
        return set(districts)
    counts: dict[str, int] = {}
    total = 0
    for tower in scene.towers:
        if tower.district == ".root":
            continue
        total += 1
        parts = tower.district.split("/")
        for i in range(1, len(parts) + 1):
            prefix = "/".join(parts[:i])
            counts[prefix] = counts.get(prefix, 0) + 1
    if total == 0:
        return set()

    children: dict[str, set[str]] = {}
    for prefix in counts:
        if "/" in prefix:
            children.setdefault(prefix.rsplit("/", 1)[0], set()).add(prefix)

    result: set[str] = set()

    def visit(prefix: str) -> None:
        kids = children.get(prefix)
        if kids and counts[prefix] / total > threshold:
            for kid in kids:
                visit(kid)
        else:
            result.add(prefix)

    for top in (prefix for prefix in counts if "/" not in prefix):
        visit(top)
    return result


def _balanced_cut(scene: _HasTowers, cap: int) -> set[str]:
    """Pick district prefixes by a scale-free, deterministic balanced peel."""
    counts: dict[str, int] = {}
    total = 0
    children: dict[str, set[str]] = {}
    for tower in scene.towers:
        if tower.district == ".root":
            continue
        total += 1
        parts = tower.district.split("/")
        for i in range(1, len(parts) + 1):
            prefix = "/".join(parts[:i])
            counts[prefix] = counts.get(prefix, 0) + 1
    if total == 0:
        return set()

    for prefix in counts:
        if "/" in prefix:
            children.setdefault(prefix.rsplit("/", 1)[0], set()).add(prefix)

    frontier: set[str] = {prefix for prefix in counts if "/" not in prefix}
    weight = dict(counts)
    split: set[str] = set()
    while len(frontier) < cap:
        mean = sum(weight[f] for f in frontier) / len(frontier)
        splittable = [f for f in frontier if f not in split and children.get(f)]
        candidates = [f for f in splittable if weight[f] > mean]
        if not candidates:
            # Frontier must not halt while budget remains; fall back to any splittable node.
            candidates = splittable
            if not candidates:
                break
        target = sorted(candidates, key=lambda p: (-weight[p], p))[0]
        kids = children[target]
        direct = counts[target] - sum(counts[kid] for kid in kids)
        budget = cap - len(frontier) + (0 if direct > 0 else 1)
        if direct > 0:
            weight[target] = direct
            split.add(target)
        else:
            frontier = frontier - {target}
        if len(kids) <= budget:
            frontier |= kids
        else:
            # Too many children to fit; keep only the largest that fit.
            frontier |= set(sorted(kids, key=lambda p: (-counts[p], p))[:budget])
            break
    return frontier


def district_cut(
    scene: _HasTowers,
    *,
    method: str = "balanced",
    threshold: float = _DISTRICT_SPLIT,
    cap: int = _DISTRICT_CAP,
    districts: frozenset[str] | None = None,
) -> set[str]:
    """Dispatch to the selected district-cut algorithm (balanced or adaptive)."""
    if districts is not None:
        return set(districts)
    if method == "balanced":
        return _balanced_cut(scene, cap)
    if method == "adaptive":
        return _district_cut(scene, threshold)
    if method == "leaf":  # one district per tower (styles that pre-group by building)
        return {t.district for t in scene.towers if t.district != ".root"}
    raise ValueError(f"unknown district cut method: {method!r}")


def _district_groups(
    scene: _HasTowers,
    districts: frozenset[str] | None = None,
    *,
    method: str = "balanced",
    cap: int = _DISTRICT_CAP,
    threshold: float = _DISTRICT_SPLIT,
) -> dict[str, list[Tower]]:
    """Map each meaningful district prefix to the towers that live under it."""
    cut = district_cut(scene, method=method, cap=cap, threshold=threshold, districts=districts)
    groups: dict[str, list[Tower]] = {}
    for tower in scene.towers:
        if tower.district == ".root":
            continue
        parts = tower.district.split("/")
        for i in range(len(parts), 0, -1):
            prefix = "/".join(parts[:i])
            if prefix in cut:
                groups.setdefault(prefix, []).append(tower)
                break
    return groups


def _overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    """Axis-aligned overlap test for two ``(x0, y0, x1, y1)`` label boxes."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


#: Directory-label font size, shared by both projections (canvas pixels).
_LABEL_SIZE = 12.5
#: Default district floor-outline stroke (overridden per-palette via ``box_stroke``).
_BOX_STROKE = "#bfe0d2"


def _box_attrs(stroke: str) -> str:
    """A district's faint ground outline (the floor parallelogram), shared by both."""
    return (
        f'fill="#aab6e0" fill-opacity="0.06" stroke="{stroke}" '
        'stroke-width="1.3" stroke-opacity="0.7" stroke-linejoin="round" '
        'stroke-dasharray="4 3"'
    )


#: ``voxel-plot`` label styling: gap above the tallest roof, halo behind a soft
#: fill (two ``<text>`` elements). Colors default to the dark theme; palette overrides.
_VOXEL_LABEL_GAP = 13.0
_VOXEL_LABEL_FILL = "#cfe4da"
_VOXEL_LABEL_HALO = "#08150f"


def _voxel_halo(color: str) -> str:
    return f'stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-opacity="0.85"'


#: ``oblique`` label styling with a snugger gap and painted stroke outline.
_OBLIQUE_LABEL_GAP = 5.0
_OBLIQUE_LABEL_FILL = "#eafbf4"
_OBLIQUE_LABEL_HALO = "#05100b"


def _oblique_outline(color: str, size: float = _LABEL_SIZE) -> str:
    # Scale the halo width to the font so it stays light at small sizes.
    width = max(2.0, size * 0.17)
    return (
        f'paint-order="stroke" stroke="{color}" stroke-width="{width:.2f}" '
        'stroke-linejoin="round" text-anchor="start"'
    )


#: Bound a district path's display width when prefixes are shown.
_LABEL_MAX_CHARS = 20


@dataclass(frozen=True, slots=True)
class DistrictConfig:
    """How a style groups files into districts and which layers it annotates."""

    cut: str = "balanced"
    cap: int = _DISTRICT_CAP
    threshold: float = _DISTRICT_SPLIT
    boxes: bool = True  # floor-outline underlay
    labels: bool = True  # directory-name overlay
    emphasis: bool = False  # new-district gold pulse (timelapse only)
    center_labels: bool = False  # pin labels over the district centroid, not its left edge


@dataclass(frozen=True, slots=True)
class Projection:
    """Projection adapters for rendering districts across different styles."""

    ground: Callable[[float, float], tuple[float, float]]
    footprint: Callable[[list[Tower]], list[tuple[float, float]]]
    height_scale: float
    label_gap: float
    emit_label: Callable[[float, float, str, float, str | None, str | None], str]


def iso_projection(scene: VoxelScene) -> Projection:
    """The ``voxel-plot`` (isometric) district projection bound to *scene*."""

    def ground(gx: float, gy: float) -> tuple[float, float]:
        return iso(gx, gy, scene.view_rot)

    def footprint(towers: list[Tower]) -> list[tuple[float, float]]:
        gx0 = min(t.grid_x for t in towers)
        gx1 = max(t.grid_x for t in towers)
        gy0 = min(t.grid_y for t in towers)
        gy1 = max(t.grid_y for t in towers)
        return [
            (gx0 - 0.5, gy0 - 0.5),
            (gx1 + 0.5, gy0 - 0.5),
            (gx1 + 0.5, gy1 + 0.5),
            (gx0 - 0.5, gy1 + 0.5),
        ]

    def emit_label(
        px: float, py: float, name: str, size: float, ink: str | None, halo_color: str | None
    ) -> str:
        # A palette overriding ink also gets weight 600; dark default keeps 400.
        lead = 'text-anchor="start"' + (' font-weight="600"' if ink else "")
        halo_attr = _voxel_halo(halo_color or _VOXEL_LABEL_HALO)
        content = html.escape(name)
        halo = text(px, py, content, fill="none", size=size, extra=f"{lead} {halo_attr}")
        face = text(px, py, content, fill=ink or _VOXEL_LABEL_FILL, size=size, extra=lead)
        return halo + face

    return Projection(ground, footprint, 1.0, _VOXEL_LABEL_GAP, emit_label)


def oblique_projection(scene: ObliqueScene) -> Projection:
    """The ``oblique`` (cabinet-oblique) district projection bound to *scene*."""
    params = scene.params

    def ground(gx: float, gy: float) -> tuple[float, float]:
        return _ground(gx, gy, params)

    def footprint(towers: list[Tower]) -> list[tuple[float, float]]:
        gx0 = min(t.grid_x for t in towers)
        gx1 = max(t.grid_x for t in towers) + 1
        gy0 = min(t.grid_y for t in towers)
        gy1 = max(t.grid_y for t in towers) + 1
        return [(gx0, gy0), (gx1, gy0), (gx1, gy1), (gx0, gy1)]

    def emit_label(
        px: float, py: float, name: str, size: float, ink: str | None, halo_color: str | None
    ) -> str:
        outline = _oblique_outline(halo_color or _OBLIQUE_LABEL_HALO, size)
        extra = outline + (' font-weight="600"' if ink else "")
        content = html.escape(name)
        return text(px, py, content, fill=ink or _OBLIQUE_LABEL_FILL, size=size, extra=extra)

    return Projection(ground, footprint, params.height_scale, _OBLIQUE_LABEL_GAP, emit_label)


def district_groups(
    scene: VoxelScene | ObliqueScene,
    cfg: DistrictConfig,
    locked: frozenset[str] | None = None,
    *,
    cap: int | None = None,
) -> dict[str, list[Tower]]:
    """Group *scene*'s towers into *cfg*'s districts (``cap`` overrides ``cfg.cap``)."""
    return _district_groups(
        scene,
        locked,
        method=cfg.cut,
        cap=cap if cap is not None else cfg.cap,
        threshold=cfg.threshold,
    )


def _footprint_points(
    towers: list[Tower], scene: VoxelScene | ObliqueScene, banner: BannerLayout, proj: Projection
) -> str:
    """Calculate the footprint points in canvas pixels."""
    points: list[str] = []
    for gx, gy in proj.footprint(towers):
        x, y = proj.ground(gx, gy)
        px = banner.content_tx + (x + scene.offset_x) * banner.scale
        py = banner.content_ty + (y + scene.offset_y) * banner.scale
        points.append(f"{px:.1f},{py:.1f}")
    return " ".join(points)


def draw_boxes(
    groups: dict[str, list[Tower]],
    scene: VoxelScene | ObliqueScene,
    banner: BannerLayout,
    proj: Projection,
    box_stroke: str = _BOX_STROKE,
) -> str:
    """Draw floor outlines under each district (underlay layer)."""
    attrs = _box_attrs(box_stroke)
    return "".join(
        f'<polygon points="{_footprint_points(towers, scene, banner, proj)}" {attrs}/>'
        for _, towers in sorted(groups.items())
    )


def _shorten_path(path: str) -> str:
    """Keep the first and last segment, eliding the middle of a deep path."""
    if len(path) <= _LABEL_MAX_CHARS:
        return path
    segs = path.split("/")
    if len(segs) <= 2:
        return path
    return f"{segs[0]}/…/{segs[-1]}"


def _centroid_anchor(
    towers: list[Tower], scene: VoxelScene | ObliqueScene, proj: Projection
) -> tuple[float, float]:
    """Content-space ``(x, roof_top)`` of the building nearest the district centroid."""
    mean_gx = sum(t.grid_x for t in towers) / len(towers)
    mean_gy = sum(t.grid_y for t in towers) / len(towers)
    pick = min(
        towers,
        key=lambda t: ((t.grid_x - mean_gx) ** 2 + (t.grid_y - mean_gy) ** 2, t.grid_x, t.grid_y),
    )
    gx, gy = proj.ground(pick.grid_x, pick.grid_y)
    return gx + scene.offset_x, gy - pick.height * proj.height_scale + scene.offset_y


def draw_labels(
    groups: dict[str, list[Tower]],
    scene: VoxelScene | ObliqueScene,
    banner: BannerLayout,
    proj: Projection,
    label_ink: str | None = None,
    label_halo: str | None = None,
    *,
    show_prefix: bool = False,
    center: bool = False,
    ts: float = 1.0,
    box_ts: float = 1.0,
) -> str:
    """Draw one label per district (overlay layer).

    ``show_prefix`` shows the elided full path instead of the bare leaf. ``center``
    pins the label over the district's centroid building instead of its left edge.
    ``ts`` is the render scale; ``box_ts`` is the collision scale, held fixed so the
    text knob can't change which labels survive.
    """
    size = _LABEL_SIZE * ts
    gap = proj.label_gap * ts
    box_size = _LABEL_SIZE * box_ts
    placed: list[tuple[float, float, float, float]] = []
    out: list[str] = []
    for path, towers in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        name = _shorten_path(path) if show_prefix else path.split("/")[-1]
        # Edge-fit on the rendered width so big text never runs off-canvas.
        text_w = 0.62 * size * len(name) + 4.0 * ts
        if center:
            anchor, top = _centroid_anchor(towers, scene, proj)
        else:
            anchor = min(proj.ground(t.grid_x, t.grid_y)[0] for t in towers) + scene.offset_x
            top = (
                min(
                    proj.ground(t.grid_x, t.grid_y)[1] - t.height * proj.height_scale
                    for t in towers
                )
                + scene.offset_y
            )
        anchor_x = banner.content_tx + anchor * banner.scale
        py = banner.content_ty + top * banner.scale - gap
        # Centred labels clamp into the page; edge labels keep their anchor even
        # left of the pad (matches worker/render/districts.js).
        px = (
            min(max(anchor_x - text_w / 2, banner.pad), banner.width - 6 - text_w)
            if center
            else min(anchor_x, max(banner.pad, banner.width - 6 - text_w))
        )
        box_w = 0.62 * box_size * len(name) + 4.0 * box_ts
        box_h = 1.3 * box_size
        box = (px, py - box_h, px + box_w, py + box_h * 0.25)
        if any(_overlaps(box, other) for other in placed):
            continue
        placed.append(box)
        out.append(proj.emit_label(px, py, name, size, label_ink, label_halo))
    return "".join(out)


def draw_emphasis(
    groups: dict[str, list[Tower]],
    scene: VoxelScene | ObliqueScene,
    banner: BannerLayout,
    proj: Projection,
    pulse: set[str],
    intensity: float,
) -> str:
    """Draw a gold pulsing boundary around the pulse districts."""
    glow = max(0.0, min(1.0, intensity))
    if glow <= 0.0:
        return ""
    out: list[str] = []
    for path, towers in sorted(groups.items()):
        if path not in pulse:
            continue
        pts = _footprint_points(towers, scene, banner, proj)
        out.append(
            f'<polygon points="{pts}" fill="#ffd166" fill-opacity="{glow * 0.12:.3f}" '
            f'stroke="#ffd166" stroke-width="{2.0 + 11.0 * glow:.1f}" '
            f'stroke-opacity="{glow * 0.30:.3f}" stroke-linejoin="round"/>'
        )
        out.append(
            f'<polygon points="{pts}" fill="none" stroke="#ffe9a0" '
            f'stroke-width="{1.4 + 2.2 * glow:.1f}" stroke-opacity="{glow:.3f}" '
            'stroke-linejoin="round"/>'
        )
    return "".join(out)
