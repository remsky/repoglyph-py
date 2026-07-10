from __future__ import annotations

from repoglyph.models import SourceFile, filter_commits, sha_label, skip_commons


def test_sha_label_truncates_hex_but_keeps_marker() -> None:
    assert sha_label("abc1234def5678") == "abc1234"
    assert sha_label("abc1234def5678+staged") == "abc1234+staged"
    assert sha_label("abc1234def5678+staged", 9) == "abc1234de+staged"


def test_filter_commits_reroots_and_prunes_like_filter_files() -> None:
    commits = [
        ["src/app.py", "src/tests/test_app.py", "docs/guide.md"],
        ["docs/guide.md"],
        ["src/util.py"],
    ]
    assert filter_commits(commits) is commits
    assert filter_commits(commits, start_dir="src", skip_dirs=["tests"]) == [
        ["app.py"],
        ["util.py"],
    ]
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
