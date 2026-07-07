"""Cross-language parity contract with the ``worker/`` JS port.

Byte-identical SVG across the two renderers is explicitly *not* a goal; what
must agree is the semantic layer: file categorization, fingerprint metrics,
the balanced district cut, the oblique/skyline/highrise packing layouts, and
the palette values.
This test computes those from Python against ``tests/parity/expected.json``
(refresh with ``REPOGLYPH_REGEN_GOLDENS=1``); ``worker/test/parity.test.js``
checks the JS port against the *same* file, keeping the two honest.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from repoglyph.metrics import compute_metrics
from repoglyph.models import CityData, SourceFile
from repoglyph.palette import categorize
from repoglyph.palettes import PALETTES
from repoglyph.render import STYLES, StyleParams
from repoglyph.render.districts import district_cut

_DIR = Path(__file__).parent / "parity"
_REGEN = os.environ.get("REPOGLYPH_REGEN_GOLDENS") == "1"


def _compute() -> dict:
    fixture = json.loads((_DIR / "fixture.json").read_text(encoding="utf-8"))
    files = [SourceFile(f["path"], size=f["size"]) for f in fixture["files"]]
    data = CityData(
        repo="acme/widget",
        files=files,
        touches=fixture["touches"],
        commit_window=30,
    )
    metrics = compute_metrics(data)
    scene = STYLES["oblique"].build(files, StyleParams())
    towers = sorted(scene.towers, key=lambda t: (t.district, t.grid_x, t.grid_y))
    skyline = STYLES["skyline"].build(files, StyleParams())
    sky_towers = sorted(skyline.towers, key=lambda t: (t.district, t.grid_x, t.grid_y))
    highrise = STYLES["highrise"].build(files, StyleParams())
    hr_towers = sorted(highrise.towers, key=lambda b: (b.district, b.grid_x, b.grid_y))
    return {
        "categorize": {case: categorize(case) for case in fixture["categorize_cases"]},
        "metrics": {
            "file_count": metrics.file_count,
            "dir_count": metrics.dir_count,
            "max_depth": metrics.max_depth,
            "largest_district": metrics.largest_district,
            "largest_district_share": metrics.largest_district_share,
            "modularity": metrics.modularity,
        },
        "balanced_cut": {
            str(cap): sorted(district_cut(scene, method="balanced", cap=cap)) for cap in (6, 14)
        },
        "oblique_layout": [
            {
                "district": t.district,
                "x": t.grid_x,
                "y": t.grid_y,
                "files": [cube.file.path for cube in t.cubes],
            }
            for t in towers
        ],
        "skyline_layout": [
            {
                "district": t.district,
                "x": t.grid_x,
                "y": t.grid_y,
                "files": [cube.file.path for cube in t.cubes],
            }
            for t in sky_towers
        ],
        "highrise_layout": [
            {
                "district": b.district,
                "x": b.grid_x,
                "y": b.grid_y,
                "floors": [
                    {"name": floor.name, "rows": floor.rows, "files": [f.path for f in floor.files]}
                    for floor in b.floors
                ],
            }
            for b in hr_towers
        ],
        "palettes": {
            name: {category: list(palette.colors[category]) for category in palette.colors}
            for name, palette in PALETTES.items()
        },
    }


def test_semantics_match_expected() -> None:
    actual = _compute()
    expected_path = _DIR / "expected.json"
    if _REGEN:
        expected_path.write_text(json.dumps(actual, indent=2) + "\n", encoding="utf-8")
        return
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    assert actual == expected, (
        "cross-language parity contract drifted (set REPOGLYPH_REGEN_GOLDENS=1 to refresh, "
        "then re-run worker/test/parity.test.js)"
    )
