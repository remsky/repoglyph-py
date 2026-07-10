from __future__ import annotations

from repoglyph.metrics import FINDINGS, OVERSIZED_FILE_BYTES, STATS, compute_metrics
from repoglyph.models import CityData, SourceFile


def _city(**kwargs) -> CityData:
    files = [
        SourceFile("src/app.py", size=1_000),
        SourceFile("src/util.py", size=500),
        SourceFile("docs/guide.md", size=200),
        SourceFile("README.md", size=100),
    ]
    return CityData(repo="o/r", files=files, **kwargs)


def test_basic_counts() -> None:
    metrics = compute_metrics(_city())
    assert metrics.file_count == 4
    assert metrics.max_depth == 1
    assert metrics.largest_district == "src"
    assert metrics.contributor_count == 0


def test_modularity_exact_score_and_floor_clamp() -> None:
    # 100 * (1 - 0.5 * 0.5) * (1 - (1000 / 40000) * 0.04) = 74.925 -> 74
    assert compute_metrics(_city()).modularity == 74
    giant = CityData(repo="o/r", files=[SourceFile("src/mega.py", size=2_000_000)])
    assert compute_metrics(giant).modularity == 0


def test_empty_repo_does_not_crash() -> None:
    metrics = compute_metrics(CityData(repo="o/r"))
    assert metrics.file_count == 0
    assert metrics.largest_district == ""
    assert metrics.modularity >= 0


def test_registered_stats_compute() -> None:
    data = _city()
    metrics = compute_metrics(data)
    values = {stat.key: stat.compute(data, metrics) for stat in STATS}
    assert values["files"] == "4"
    assert values["largest_district"] == "src, 50% of files"
    assert all(value is None or isinstance(value, str) for value in values.values())


def test_change_coupling_ranks_broadly_coupled_files() -> None:
    data = _city(
        commit_files=[
            ["src/app.py", "src/util.py"],
            ["src/app.py", "src/util.py", "gone/old.py"],
            ["src/app.py", "docs/guide.md"],
            ["src/app.py", "docs/guide.md"],
            ["src/app.py", "README.md"],  # one shared commit: below the pair threshold
        ]
    )
    (finding,) = [f for f in FINDINGS if f.key == "change_coupling"]
    rows = finding.compute(data)
    assert rows[0] == (
        "`src/app.py`",
        "2",
        "4",
        "`docs/guide.md` (2), `src/util.py` (2)",
    )
    assert {row[0] for row in rows} == {"`src/app.py`", "`src/util.py`", "`docs/guide.md`"}
    assert len(finding.columns) == len(rows[0])


def test_change_coupling_skips_bulk_commits_and_missing_data() -> None:
    files = [SourceFile(f"pkg/f{i:02}.py", size=10) for i in range(40)]
    bulk = [f.path for f in files]
    data = CityData(repo="o/r", files=files, commit_files=[bulk, bulk, bulk])
    (finding,) = [f for f in FINDINGS if f.key == "change_coupling"]
    assert finding.compute(data) == []
    assert finding.compute(_city()) == []  # no commit_files gathered


def test_oversized_files_finding() -> None:
    data = _city()
    data.files.append(SourceFile("src/huge.py", size=OVERSIZED_FILE_BYTES + 1))
    (finding,) = [f for f in FINDINGS if f.key == "oversized_files"]
    rows = finding.compute(data)
    assert rows == [("`src/huge.py`", "39.1 KB")]
    assert len(finding.columns) == len(rows[0])
