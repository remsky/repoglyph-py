from __future__ import annotations

import json
from pathlib import Path

import pytest

from repoglyph.cache import CACHE_NAME, load_city, repo_stem, save_city
from repoglyph.models import CityData, SourceFile


def _city() -> CityData:
    return CityData(
        repo="owner/repo",
        files=[SourceFile(path="src/a.py", size=10)],
        touches={"src/a.py": 3},
        commit_files=[["src/a.py"], ["src/a.py", "src/b.py"]],
        commit_window=50,
        head_sha="abc123",
    )


def test_repo_stem_replaces_path_separators() -> None:
    assert repo_stem("owner/repo") == "owner_repo"
    assert repo_stem("../owner\\repo:evil") == ".._owner_repo_evil"


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    city = _city()
    assert save_city(city, tmp_path) == tmp_path / CACHE_NAME
    assert load_city(tmp_path) == city


def test_load_city_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_city(tmp_path)


def test_load_city_rejects_incompatible_format(tmp_path: Path) -> None:
    path = save_city(_city(), tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["format_version"] = 0
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="format_version"):
        load_city(tmp_path)
