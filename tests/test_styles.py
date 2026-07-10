"""Registry safety: a broken or malformed style fails loudly and alone."""

from __future__ import annotations

import xml.dom.minidom

import pytest

from repoglyph.cli import build_parser
from repoglyph.models import CityData, SourceFile
from repoglyph.render import STYLES, StyleSpec, render
from repoglyph.render.styles import _build_oblique

EXPECTED_STYLES = {"highrise", "oblique", "skyline"}

_EDGE_CITIES = {
    "empty": [],
    "single-root-file": [SourceFile("README.md", size=100)],
    "deep-chain": [SourceFile("a/b/c/d/e/f/mod.py", size=2_000)],
    "wide-root": [SourceFile(f"f{i}.py", size=10 * (i + 1)) for i in range(30)],
}


def test_registry_is_complete() -> None:
    # a dropped style silently drops its golden coverage
    assert set(STYLES) == EXPECTED_STYLES


def test_malformed_spec_fails_at_construction() -> None:
    with pytest.raises(ValueError):
        StyleSpec(_build_oblique, lambda *a, **k: "", summary="")
    with pytest.raises(ValueError):
        StyleSpec("not-callable", lambda *a, **k: "", summary="x")
    with pytest.raises(TypeError):
        StyleSpec(_build_oblique, lambda *a, **k: "")  # summary is required


@pytest.mark.parametrize("style", sorted(STYLES))
@pytest.mark.parametrize("shape", sorted(_EDGE_CITIES))
def test_style_survives_edge_inputs(style: str, shape: str) -> None:
    city = CityData(repo="edge/case", files=_EDGE_CITIES[shape], touches={})
    svg = render(city, style=style)
    assert svg.startswith("<svg")
    xml.dom.minidom.parseString(svg)


def test_cli_derives_style_menu_and_knobs() -> None:
    parser = build_parser()
    args = parser.parse_args([])
    # Product defaults come from field metadata (cli_default), not the library defaults.
    assert args.shear == 0.0
    assert args.streets == 1
    assert args.detail == 24
    assert args.label_prefix is True
    # Every registered style is a valid --style choice with its summary in the
    # help (compare whitespace-normalized: argparse wraps lines).
    help_text = " ".join(parser.format_help().split())
    for name, spec in STYLES.items():
        parser.parse_args(["--style", name])
        assert spec.summary in help_text
