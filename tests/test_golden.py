"""Golden snapshot harness.

Renders a fixed synthetic :class:`CityData` through every style in
:data:`repoglyph.render.STYLES`, asserting the SVG is byte-for-byte identical to
committed baselines in ``tests/goldens``. Refresh baselines by running the suite
once with ``REPOGLYPH_REGEN_GOLDENS=1`` set.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from repoglyph.models import CityData, SourceFile
from repoglyph.render import STYLES, StyleParams, render

_GOLDENS = Path(__file__).parent / "goldens"
_REGEN = os.environ.get("REPOGLYPH_REGEN_GOLDENS") == "1"


def _golden_city() -> CityData:
    """Structurally rich fixture exercising both district-cut regimes.

    Two containers at different scales so the adaptive-vs-balanced cut diverges:
    ``pkg/`` is oversized (> 35% of files, both methods split it) and ``src/`` is
    moderate (below the 0.35 adaptive threshold, so only balanced peels it).
    ``docs``/``scripts``/``.github`` stay whole; varied sizes/extensions and a few
    ``touches`` round it out.
    """
    files = [
        # Oversized container: pkg/ holds > 35% of files; both cut methods split it.
        SourceFile("pkg/core/engine.py", size=8_400),
        SourceFile("pkg/core/parser.py", size=5_100),
        SourceFile("pkg/core/utils.py", size=2_300),
        SourceFile("pkg/core/config.json", size=600),
        SourceFile("pkg/io/reader.py", size=3_900),
        SourceFile("pkg/io/writer.py", size=4_200),
        SourceFile("pkg/io/formats.py", size=1_700),
        SourceFile("pkg/tests/test_core.py", size=2_800),
        SourceFile("pkg/tests/test_io.py", size=2_100),
        SourceFile("pkg/tests/fixtures.py", size=900),
        # Moderate container: src/ is below the 0.35 adaptive threshold but above
        # the balanced frontier mean, the case the two methods disagree on.
        SourceFile("src/ui/home.py", size=1_500),
        SourceFile("src/ui/views.py", size=2_200),
        SourceFile("src/ui/widgets.py", size=1_800),
        SourceFile("src/api/routes.py", size=2_600),
        SourceFile("src/api/models.py", size=1_400),
        # Small top-level dirs that should stay whole.
        SourceFile("docs/index.md", size=1_200),
        SourceFile("docs/guide.md", size=2_600),
        SourceFile("scripts/build.py", size=700),
        SourceFile(".github/workflows/ci.yml", size=450),
        # Root files.
        SourceFile("README.md", size=1_500),
        SourceFile("setup.py", size=800),
        SourceFile("logo.png", size=42_000),
    ]
    return CityData(
        repo="acme/widget",
        files=files,
        touches={
            "pkg/core/engine.py": 9,
            "pkg/io/writer.py": 4,
            "pkg/tests/test_core.py": 2,
            "src/api/routes.py": 3,
            "README.md": 1,
        },
        commit_window=30,
    )


def _read_golden(name: str) -> str:
    return (_GOLDENS / f"{name}.svg").read_text(encoding="utf-8")


def _write_golden(name: str, svg: str) -> None:
    _GOLDENS.mkdir(parents=True, exist_ok=True)
    (_GOLDENS / f"{name}.svg").write_text(svg, encoding="utf-8")


@pytest.mark.parametrize("style", sorted(STYLES))
def test_style_matches_golden(style: str) -> None:
    city = _golden_city()
    svg = render(city, style=style)
    # Same input renders byte-identically twice.
    assert render(city, style=style) == svg, f"{style}: render is non-deterministic"

    if _REGEN:
        _write_golden(style, svg)
        return

    expected = _read_golden(style)
    assert svg == expected, (
        f"golden mismatch for style {style!r} (set REPOGLYPH_REGEN_GOLDENS=1 to refresh)"
    )


#: Param variants reachable only via flags.
_PARAM_GOLDENS = {
    "oblique-shear6": ("oblique", StyleParams(shear=6.0)),
}


@pytest.mark.parametrize("name", sorted(_PARAM_GOLDENS))
def test_param_variant_matches_golden(name: str) -> None:
    style, params = _PARAM_GOLDENS[name]
    city = _golden_city()
    svg = render(city, style=style, params=params)
    assert render(city, style=style, params=params) == svg, f"{name}: render is non-deterministic"

    if _REGEN:
        _write_golden(name, svg)
        return

    expected = _read_golden(name)
    assert svg == expected, (
        f"golden mismatch for param variant {name!r} (set REPOGLYPH_REGEN_GOLDENS=1 to refresh)"
    )
