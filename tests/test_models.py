from __future__ import annotations

from repoglyph.models import SourceFile, skip_commons


def test_skip_commons_drops_lockfiles_everywhere() -> None:
    files = [
        SourceFile("uv.lock", size=100),
        SourceFile("vendor/yarn.lock", size=100),
        SourceFile("src/app.py", size=100),
    ]
    touches = {"uv.lock": 999, "src/app.py": 5, "gone/Cargo.lock": 7}
    kept_files, kept_touches = skip_commons(files, touches)
    assert [f.path for f in kept_files] == ["src/app.py"]
    assert kept_touches == {"src/app.py": 5}


def test_skip_commons_keeps_inputs_when_result_would_be_empty() -> None:
    files = [SourceFile("uv.lock", size=100)]
    touches = {"uv.lock": 999}
    assert skip_commons(files, touches) == (files, touches)
