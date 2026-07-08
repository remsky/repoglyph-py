from __future__ import annotations

import pytest

from repoglyph.palette import categorize


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("src/main.py", "code"),
        ("deep/nested/Component.tsx", "code"),
        ("pyproject.toml", "conf"),
        ("config/prod.env", "conf"),
        # A bare dotfile has no extension, so it falls through to "other".
        (".env", "other"),
        ("README.md", "docs"),
        ("docs/guide.rst", "docs"),
        ("logo.PNG", "asset"),
        ("model.onnx", "asset"),
        ("Makefile", "other"),
        ("LICENSE", "other"),
    ],
)
def test_categorize(path: str, expected: str) -> None:
    assert categorize(path) == expected
