"""Compose the render layers into a complete banner SVG.

``render`` resolves the style's renderer + annotation layers from ``STYLES``,
fits the camera, and assembles the city and HUD into one deterministic SVG.
"""

from __future__ import annotations

import dataclasses

from repoglyph.geometry import (
    BANNER_HEIGHT,
    BANNER_WIDTH,
    fit_banner,
)
from repoglyph.metrics import RepoMetrics, compute_metrics
from repoglyph.models import CityData, SourceFile, filter_files
from repoglyph.palettes import Palette, resolve_palette
from repoglyph.render.districts import district_groups, draw_boxes, draw_labels
from repoglyph.render.overlay import render_legend, render_panel
from repoglyph.render.scene import Tower
from repoglyph.render.styles import STYLES, StyleParams
from repoglyph.render.svg import assemble_document

__all__ = ["render"]

#: District cap when none is given.
_DEFAULT_DETAIL = 14
#: Baseline text bump folded into the HUD scale; caller's ``text_scale`` rides on top.
_TEXT_BASE = 1.25
#: Hard ceiling on buildings drawn for very large repositories.
_MAX_BUILDINGS = 40000


def _cap_files(
    files: list[SourceFile], touches: dict[str, int]
) -> tuple[list[SourceFile], dict[str, int]]:
    """Downsample to a drawable size, keeping touched + largest files per dir."""
    if len(files) <= _MAX_BUILDINGS:
        return files, touches
    factor = _MAX_BUILDINGS / len(files)
    by_dir: dict[str, list[SourceFile]] = {}
    for file in files:
        slash = file.path.rfind("/")
        by_dir.setdefault(file.path[:slash] if slash != -1 else "", []).append(file)

    by_size = lambda file: (-file.size, file.path)  # noqa: E731
    kept: list[SourceFile] = []
    for group in by_dir.values():
        keep_n = max(1, round(len(group) * factor))  # >=1 keeps the dir on the map
        if keep_n >= len(group):
            kept.extend(group)
            continue
        touched = sorted((f for f in group if touches.get(f.path, 0) > 0), key=by_size)
        rest = sorted((f for f in group if touches.get(f.path, 0) <= 0), key=by_size)
        pick = touched[:keep_n]
        for file in rest:
            if len(pick) >= keep_n:
                break
            pick.append(file)
        kept.extend(pick)

    keep_paths = {file.path for file in kept}
    return kept, {p: c for p, c in touches.items() if p in keep_paths}


def _drawn_district(groups: dict[str, list[Tower]], file_count: int) -> tuple[str, float] | None:
    """The biggest district actually drawn (by file count), for the panel readout."""
    if not groups or file_count == 0:
        return None
    best_name: str | None = None
    best_count = -1
    for name, towers in groups.items():
        count = sum(len(tower.cubes) for tower in towers)
        if count > best_count or (
            count == best_count and best_name is not None and name < best_name
        ):
            best_count = count
            best_name = name
    assert best_name is not None
    return best_name, best_count / file_count


def _most_active_district(
    groups: dict[str, list[Tower]], touches: dict[str, int]
) -> tuple[str, float] | None:
    """The drawn district with the most recent churn, as a share of all churn."""
    total = sum(touches.values())
    if total <= 0:
        return None
    best_name: str | None = None
    best_sum = 0
    for name, towers in groups.items():
        summed = sum(touches.get(cube.file.path, 0) for tower in towers for cube in tower.cubes)
        if summed > best_sum or (summed == best_sum and best_name is not None and name < best_name):
            best_sum = summed
            best_name = name
    if best_name is None or best_sum <= 0:
        return None
    return best_name, best_sum / total


def _panel_metrics(
    metrics: RepoMetrics, groups: dict[str, list[Tower]], touches: dict[str, int]
) -> RepoMetrics:
    """Override the panel's "most files"/"most active" stats to the drawn cut.

    The biggest drawn district matches a visible label; ``modularity`` stays on
    the original top-level share so the score is detail-independent.
    """
    drawn = _drawn_district(groups, metrics.file_count)
    active = _most_active_district(groups, touches)
    return dataclasses.replace(
        metrics,
        largest_district=drawn[0] if drawn else metrics.largest_district,
        largest_district_share=drawn[1] if drawn else metrics.largest_district_share,
        active_district=active[0] if active else None,
        active_district_share=active[1] if active else 0.0,
    )


def render(
    data: CityData,
    *,
    width: int = BANNER_WIDTH,
    height: int = BANNER_HEIGHT,
    full: bool = False,
    style: str = "oblique",
    params: StyleParams | None = None,
    palette: Palette | None = None,
    detail: int = _DEFAULT_DETAIL,
    text_scale: float = 1.0,
    weight: str = "churn",
    label_prefix: bool = False,
    show_labels: bool = True,
    border: bool = False,
    start_dir: str = "",
    skip_dirs: list[str] | None = None,
) -> str:
    """Render a complete repoglyph banner as an SVG document string."""
    spec = STYLES[style]
    # `detail` rides in on the params handed to the build, matching the JS port.
    params = dataclasses.replace(params or StyleParams(), detail=detail)
    ts = _TEXT_BASE * text_scale

    # Re-root/prune, bound large repos, weight touch. All no-ops under defaults,
    # so existing callers stay byte-identical.
    files, touches = filter_files(
        data.files, data.touches, start_dir=start_dir, skip_dirs=skip_dirs or []
    )
    files, touches = _cap_files(files, touches)
    if weight == "files":
        touches = {path: 1 for path, count in touches.items() if count > 0}

    scene = spec.build(files, params)
    banner = fit_banner(scene, width=width, height=height, full=full)

    metrics = compute_metrics(dataclasses.replace(data, files=files, touches=touches))
    max_touch = max(touches.values(), default=1) or 1

    theme = palette or resolve_palette(None)
    colors, chrome = theme.colors, theme.chrome
    city = spec.render(scene, touches, max_touch, colors=colors, chrome=chrome)
    legend = render_legend(banner, colors=colors, chrome=chrome)

    # Resolve the district cut once, shared by panel stats and layout layers.
    hud_underlay = ""
    hud_overlay = ""
    cfg = spec.districts
    groups: dict[str, list[Tower]] = {}
    if cfg is not None and spec.projection is not None:
        proj = spec.projection(scene)
        groups = district_groups(scene, cfg, cap=detail)
        if cfg.boxes:
            hud_underlay += draw_boxes(groups, scene, banner, proj, chrome.box_stroke)
        if cfg.labels and show_labels:
            hud_overlay += draw_labels(
                groups,
                scene,
                banner,
                proj,
                chrome.label_ink,
                chrome.label_halo,
                show_prefix=label_prefix,
                center=cfg.center_labels,
                ts=ts,
                box_ts=_TEXT_BASE,
            )
        if spec.floor_labels is not None and show_labels:
            hud_overlay += spec.floor_labels(
                scene, banner, proj, chrome.label_ink, chrome.label_halo, ts
            )

    panel = render_panel(
        data.repo,
        data.commit_window,
        touches,
        _panel_metrics(metrics, groups, touches),
        banner,
        chrome,
        truncated=data.touch_truncated,
        ts=ts,
        head_sha=data.head_sha,
    )

    return assemble_document(
        banner,
        panel=panel,
        legend=legend,
        city=city,
        chrome=chrome,
        underlay=hud_underlay,
        overlay=hud_overlay,
        border=border,
    )
