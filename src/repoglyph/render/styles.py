"""The render-style registry (skyline, highrise, oblique)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from repoglyph.models import SourceFile
from repoglyph.render.districts import (
    DistrictConfig,
    Projection,
    district_groups,
    iso_projection,
    oblique_projection,
)
from repoglyph.render.highrise import build_highrise, draw_floor_labels, render_highrise
from repoglyph.render.oblique import build_oblique, render_oblique
from repoglyph.render.skyline import build_skyline, render_skyline

__all__ = ["StyleParams", "StyleSpec", "STYLES", "district_set"]


@dataclass(frozen=True, slots=True)
class StyleParams:
    """The tunable knobs a style reads; each field belongs to one style.

    ``shear`` is the ``oblique`` camera tilt (higher = fatter side walls);
    ``streets`` is the ``skyline``/``highrise`` lane width (``0`` packs flush);
    ``detail`` is the ``highrise`` building-frontier budget (also the district-cut
    cap, threaded by ``compose.render`` so both stay in lockstep).

    Field ``metadata`` generates the CLI flag; ``cli_default`` is the product
    default when it differs from the library default here.
    """

    shear: float = field(
        default=2.0,
        metadata={
            "help": "oblique only: camera tilt; higher = fatter side walls / "
            "more 3-D, same height (try 6)",
            "cli_default": 0.0,
        },
    )
    streets: int = field(
        default=1,
        metadata={"help": "skyline/highrise: lane width between neighbourhoods; 0 = flush"},
    )
    detail: int = field(
        default=14,
        metadata={
            "help": "district label budget; more = finer sub-structure",
            "cli_default": 24,
        },
    )


#: Build a content scene from files + resolved params (+ optional timelapse hints).
_BuildScene = Callable[..., Any]
#: Draw a scene into the scaled-city ``<g>``: ``(scene, touches, max_touch, *, colors) -> str``.
_RenderCity = Callable[..., str]
#: ``scene -> Projection``: the district-annotation adapter for a scene.
_Projection = Callable[[Any], Projection]
#: Extra overlay labels a style draws beyond the district cut (highrise floors).
_FloorLabels = Callable[..., str]


@dataclass(frozen=True, slots=True)
class StyleSpec:
    """A declarative render style: a renderer plus optional district annotation."""

    build: _BuildScene
    render: _RenderCity
    summary: str = field(kw_only=True)
    projection: _Projection | None = None
    districts: DistrictConfig | None = None
    floor_labels: _FloorLabels | None = None

    def __post_init__(self) -> None:
        if not callable(self.build) or not callable(self.render):
            raise ValueError("StyleSpec.build and .render must be callable")
        if not self.summary.strip():
            raise ValueError("StyleSpec.summary must be a non-empty description")
        # projection and districts must be set together.
        if (self.projection is None) != (self.districts is None):
            raise ValueError(
                "StyleSpec.projection and .districts must be set together or both None"
            )


def _build_oblique(files: list[SourceFile], params: StyleParams, hints: Any = None) -> Any:
    return build_oblique(files, shear=params.shear, hints=hints)


def _build_skyline(files: list[SourceFile], params: StyleParams, hints: Any = None) -> Any:
    return build_skyline(files, streets=params.streets)


def _build_highrise(files: list[SourceFile], params: StyleParams, hints: Any = None) -> Any:
    return build_highrise(files, streets=params.streets, detail=params.detail)


STYLES: dict[str, StyleSpec] = {
    "skyline": StyleSpec(
        _build_skyline,
        render_skyline,
        summary="one windowed building per file in labelled neighbourhood districts",
        projection=iso_projection,
        districts=DistrictConfig(center_labels=True),
    ),
    "highrise": StyleSpec(
        _build_highrise,
        render_highrise,
        summary="one tower per neighbourhood, floors are subdirs",
        projection=iso_projection,
        districts=DistrictConfig(cut="leaf", boxes=False, center_labels=True),
        floor_labels=draw_floor_labels,
    ),
    "oblique": StyleSpec(
        _build_oblique,
        render_oblique,
        summary="the same districts in a flat cabinet-oblique view",
        projection=oblique_projection,
        districts=DistrictConfig(emphasis=True),
    ),
}


def district_set(files: list[SourceFile], style: str) -> set[str]:
    """Get the labelled district paths for *files* under *style*."""
    spec = STYLES[style]
    if spec.districts is None:
        return set()
    return set(district_groups(spec.build(files, StyleParams()), spec.districts))
