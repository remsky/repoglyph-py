from __future__ import annotations

from repoglyph.gitsource import (
    _REMOTE_RE,
    _parse_ls_tree,
    _parse_numstat,
)


def test_parse_ls_tree_keeps_blobs_with_sizes() -> None:
    output = (
        "100644 blob aaaaaaa    1234\tsrc/app.py\n"
        "100644 blob bbbbbbb     42\tREADME.md\n"
        "040000 tree ccccccc      -\tsrc\n"  # tree: skipped
        "160000 commit ddddddd     -\tvendor/lib\n"  # submodule: skipped
    )
    files = _parse_ls_tree(output)
    assert {(f.path, f.size) for f in files} == {("src/app.py", 1234), ("README.md", 42)}


def test_parse_ls_tree_handles_paths_with_spaces() -> None:
    files = _parse_ls_tree("100644 blob abc    10\tdocs/my notes.md\n")
    assert files[0].path == "docs/my notes.md"
    assert files[0].size == 10


def test_parse_numstat_sums_line_churn_per_file() -> None:
    # app.py changed in two commits (3+1 then 5+2 = 11), util.py once (2+0), plus
    # a binary asset reporting no line counts (floors to 1, still touched).
    output = "\n3\t1\tsrc/app.py\n2\t0\tsrc/util.py\n\n5\t2\tsrc/app.py\n-\t-\tassets/logo.png\n"
    assert _parse_numstat(output) == {
        "src/app.py": 11,
        "src/util.py": 2,
        "assets/logo.png": 1,
    }


def test_remote_re_extracts_slug_from_common_url_shapes() -> None:
    for url in (
        "https://github.com/owner/repo.git",
        "https://github.com/owner/repo",
        "https://github.com/owner/repo/",
        "git@github.com:owner/repo.git",
        "ssh://git@github.com/owner/repo.git",
        "https://x-access-token:tok@github.com/owner/repo.git",
    ):
        match = _REMOTE_RE.search(url)
        assert match and match.group("slug") == "owner/repo", url


def test_remote_re_rejects_non_github_remotes() -> None:
    for url in (
        "https://gitlab.com/owner/repo.git",
        "https://example.com/github.com/fake",
        "/local/bare/repo.git",
    ):
        assert _REMOTE_RE.search(url) is None, url


def test_remote_re_rejects_malformed_github_slugs() -> None:
    for url in (
        "https://github.com/owner/repo/../../evil.git",
        "https://github.com/../evil.git",
        "https://github.com/owner/..",
        "https://github.com/owner/repo:evil.git",
        "https://github.com/owner/repo\\evil.git",
    ):
        assert _REMOTE_RE.search(url) is None, url
