from __future__ import annotations

import xml.dom.minidom

from repoglyph.models import CityData, SourceFile
from repoglyph.render import StyleParams, render


def _sample_city() -> CityData:
    return CityData(
        repo="remsky/Kokoro-FastAPI",
        files=[
            SourceFile("src/app.py", size=4_200),
            SourceFile("src/models/voice.py", size=1_800),
            SourceFile("tests/test_app.py", size=900),
            SourceFile("README.md", size=300),
            SourceFile("assets/logo.png", size=50_000),
        ],
        touches={"src/app.py": 7, "README.md": 1},
        commit_window=30,
    )


def test_render_returns_well_formed_svg() -> None:
    svg = render(_sample_city())
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    # Parses as XML (raises on malformed markup).
    xml.dom.minidom.parseString(svg)


def test_render_is_deterministic() -> None:
    assert render(_sample_city()) == render(_sample_city())


def test_render_handles_empty_repo() -> None:
    svg = render(CityData(repo="o/r", files=[SourceFile("README.md")]))
    xml.dom.minidom.parseString(svg)


def test_render_escapes_repo_and_district_text() -> None:
    city = CityData(
        repo='owner/<repo>&"x"',
        files=[SourceFile("pkg/<unsafe&dir>/app.py", size=100)],
        touches={"pkg/<unsafe&dir>/app.py": 1},
    )
    svg = render(city, label_prefix=True)

    xml.dom.minidom.parseString(svg)
    assert "&lt;repo&gt;&amp;&quot;x&quot;" in svg
    assert "pkg/&lt;unsafe&amp;dir&gt;" in svg
    assert 'owner/<repo>&"x"' not in svg


def test_oblique_style_is_well_formed_and_deterministic() -> None:
    city = _sample_city()
    svg = render(city, style="oblique")
    assert svg.startswith("<svg")
    xml.dom.minidom.parseString(svg)
    assert render(city, style="oblique") == svg  # deterministic


def test_oblique_shear_changes_only_the_camera() -> None:
    # A deeper shear is a different drawing, but the camera is the only lever that
    # moved (grid cells are camera-independent).
    city = _sample_city()
    deep = render(city, style="oblique", params=StyleParams(shear=6.0))
    assert deep != render(city, style="oblique")


def test_skyline_and_highrise_are_well_formed_and_deterministic() -> None:
    city = _sample_city()
    for style in ("skyline", "highrise"):
        svg = render(city, style=style)
        assert svg.startswith("<svg")
        xml.dom.minidom.parseString(svg)
        assert render(city, style=style) == svg  # deterministic


def test_district_groups_honors_locked_cut() -> None:
    # _district_groups recomputes the cut when districts=None, but groups against
    # a provided frozenset verbatim.
    from repoglyph.render.districts import _district_groups
    from repoglyph.render.scene import build_voxel

    files = [
        SourceFile("alpha/one.py", size=100),
        SourceFile("alpha/two.py", size=200),
        SourceFile("beta/three.py", size=150),
        SourceFile("beta/sub/four.py", size=120),
        SourceFile("gamma/five.py", size=90),
    ]
    scene = build_voxel(files)

    natural = set(_district_groups(scene))
    assert natural, "fixture should yield at least one natural district"

    # Drop one district and lock to the remainder: the dropped path must not
    # appear as a group key, and every key must come from the provided set.
    dropped = sorted(natural)[0]
    locked = frozenset(natural - {dropped})
    grouped = _district_groups(scene, districts=locked)
    assert dropped not in grouped
    assert set(grouped).issubset(locked)
