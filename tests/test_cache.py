from __future__ import annotations

from pathlib import Path

from repoglyph.cache import cache_path, repo_stem


def test_repo_stem_replaces_path_separators() -> None:
    assert repo_stem("owner/repo") == "owner_repo"
    assert repo_stem("../owner\\repo:evil") == ".._owner_repo_evil"


def test_cache_path_stays_under_cache_dir() -> None:
    assert cache_path("../owner\\repo:evil", Path("cache")) == Path("cache/.._owner_repo_evil.json")
