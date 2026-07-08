"""Unit tests for the balanced district cut."""

from __future__ import annotations

import pytest

from repoglyph.models import SourceFile
from repoglyph.render.districts import district_cut
from repoglyph.render.scene import build_voxel


def test_balanced_cut_exact_result_for_small_tree() -> None:
    files = [
        SourceFile("pkg/core/a.py", size=100),
        SourceFile("pkg/io/b.py", size=120),
        SourceFile("pkg/tests/c.py", size=90),
        SourceFile("docs/intro.md", size=50),
    ]
    cut = district_cut(build_voxel(files), method="balanced")
    assert cut == {"pkg/core", "pkg/io", "pkg/tests", "docs"}


def test_balanced_cut_peels_an_oversized_container() -> None:
    # pkg/* dominates the file count, so it is peeled into its real children,
    # while small whole dirs (docs, scripts) stay intact.
    files = (
        [SourceFile(f"pkg/core/c{i}.py", size=100 + i) for i in range(5)]
        + [SourceFile(f"pkg/io/i{i}.py", size=100 + i) for i in range(5)]
        + [SourceFile(f"pkg/tests/t{i}.py", size=100 + i) for i in range(5)]
        + [SourceFile("docs/intro.md", size=50), SourceFile("docs/guide.md", size=60)]
        + [SourceFile("scripts/run.sh", size=40)]
    )
    scene = build_voxel(files)
    cut = district_cut(scene, method="balanced")

    assert "pkg" not in cut
    assert {"pkg/core", "pkg/io", "pkg/tests"} <= cut
    assert "docs" in cut  # small dir stays whole
    assert "docs/intro.md" not in cut
    assert "docs/anything" not in cut


def test_balanced_cut_descends_dominant_dir_within_cap() -> None:
    # big/ has 6 single-file subdirs and dominates; with a small cap the full
    # split overshoots, so balanced descends into big and keeps only the largest
    # children that fit the budget (ties by path ascending), leaving the rest
    # unlabeled. Frontier {big, docs, scripts} (3), cap 4 -> budget 2 -> keep the
    # two ascending subdirs; big drops out and the frontier hits the cap.
    files = [SourceFile(f"big/sub{i}/f.py", size=100) for i in range(6)]
    files += [SourceFile("docs/intro.md", size=10), SourceFile("scripts/run.sh", size=10)]
    scene = build_voxel(files)

    cap = 4
    cut = district_cut(scene, method="balanced", cap=cap)
    assert "big" not in cut  # descended, not left whole
    assert {"big/sub0", "big/sub1"} <= cut  # largest (ascending) children kept
    assert "big/sub5" not in cut  # long tail stays unlabeled
    assert {"docs", "scripts"} <= cut  # siblings preserved
    assert len(cut) <= cap


def test_balanced_cut_tie_breaks_by_path_ascending() -> None:
    # Two sibling dirs with EQUAL file counts both qualify, but the cap permits
    # only one split. The path-ascending dir ("aaa") must be the one split.
    # Frontier {aaa, zzz, small} (2, 2, 1); mean 5/3 so both 2-file dirs exceed
    # it. cap=4: aaa splits first -> {aaa/x, aaa/y, zzz, small}=4, hitting the cap
    # before zzz can split, so zzz stays whole.
    files = [
        SourceFile("aaa/x/f.py", size=100),
        SourceFile("aaa/y/f.py", size=100),
        SourceFile("zzz/x/f.py", size=100),
        SourceFile("zzz/y/f.py", size=100),
        SourceFile("small/one.py", size=100),
    ]
    scene = build_voxel(files)
    cut = district_cut(scene, method="balanced", cap=4)

    assert {"aaa/x", "aaa/y"} <= cut  # ascending sibling split
    assert "aaa" not in cut
    assert "zzz" in cut  # other sibling stayed whole
    assert len(cut) <= 4


def test_balanced_cut_keeps_split_dir_with_loose_files() -> None:
    files = (
        [SourceFile(f"pkg/core/c{i}.py", size=100) for i in range(5)]
        + [SourceFile(f"pkg/io/i{i}.py", size=100) for i in range(5)]
        + [SourceFile(f"pkg/loose{i}.py", size=100) for i in range(4)]
        + [SourceFile("docs/intro.md", size=50)]
    )
    scene = build_voxel(files)
    cut = district_cut(scene, method="balanced")

    assert {"pkg/core", "pkg/io"} <= cut
    assert "pkg" in cut
    assert "docs" in cut


def test_adaptive_cut_splits_only_past_the_threshold() -> None:
    # pkg/ is 10/18 files (over 0.35) so adaptive splits it; src/ at 5/18 stays whole.
    files = (
        [SourceFile(f"pkg/core/c{i}.py", size=100) for i in range(4)]
        + [SourceFile(f"pkg/io/i{i}.py", size=100) for i in range(3)]
        + [SourceFile(f"pkg/tests/t{i}.py", size=100) for i in range(3)]
        + [SourceFile(f"src/ui/u{i}.py", size=100) for i in range(3)]
        + [SourceFile(f"src/api/a{i}.py", size=100) for i in range(2)]
        + [SourceFile("docs/intro.md", size=50), SourceFile("docs/guide.md", size=60)]
        + [SourceFile("scripts/run.sh", size=40)]
    )
    scene = build_voxel(files)

    adaptive = district_cut(scene, method="adaptive")
    assert adaptive == {"pkg/core", "pkg/io", "pkg/tests", "src", "docs", "scripts"}

    balanced = district_cut(scene, method="balanced")
    assert {"src/ui", "src/api"} <= balanced
    assert "src" not in balanced


def test_district_cut_unknown_method_raises() -> None:
    scene = build_voxel([SourceFile("pkg/a.py", size=100)])
    with pytest.raises(ValueError):
        district_cut(scene, method="nonsense")
