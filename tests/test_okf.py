from __future__ import annotations

from pathlib import Path

from repoglyph.models import CityData, SourceFile
from repoglyph.okf import build_okf_bundle, write_okf_bundle


def _city() -> CityData:
    files = [
        SourceFile("src/app.py", size=50_000),
        SourceFile("src/util.py", size=500),
        SourceFile("docs/guide.md", size=200),
        SourceFile("index/config.yml", size=10),
        SourceFile("README.md", size=100),
    ]
    touches = {"src/app.py": 120, "docs/guide.md": 4, "gone/old.py": 9}
    return CityData(
        repo="owner/repo",
        files=files,
        touches=touches,
        commit_window=50,
        head_sha="abc1234def5678",
    )


def _frontmatter_of(doc: str) -> str:
    assert doc.startswith("---\n")
    return doc.split("\n---\n", 1)[0]


def test_every_concept_has_typed_frontmatter() -> None:
    bundle = build_okf_bundle(_city())
    for path, doc in bundle.items():
        name = Path(path).stem
        if name in {"index", "log"}:
            assert not doc.startswith("---"), f"{path} is reserved and must have no frontmatter"
        else:
            assert "type: " in _frontmatter_of(doc), f"{path} is missing a type"


def test_repository_doc_contents() -> None:
    doc = build_okf_bundle(_city())["repository.md"]
    assert 'type: "Repository"' in doc
    assert 'resource: "https://github.com/owner/repo"' in doc
    assert "modularity" in doc
    # Flat bundle: district bullets are unlinked and route to the stats table.
    assert "* src - " in doc
    assert "[districts](districts/index.md)" in doc
    assert "[src](districts/src.md)" not in doc
    linked = build_okf_bundle(_city(), inventory=True)["repository.md"]
    assert "[src](districts/src.md)" in linked


def test_reserved_district_name_is_renamed() -> None:
    bundle = build_okf_bundle(_city(), inventory=True)
    assert "districts/index-district.md" in bundle
    assert "[index](districts/index-district.md)" in bundle["index.md"]


def test_root_files_district() -> None:
    bundle = build_okf_bundle(_city(), inventory=True)
    assert "districts/root.md" in bundle
    doc = bundle["districts/root.md"]
    assert "Files at the repository root." in doc
    assert "**repository root**" in doc
    assert "- `README.md` (100 B)" in doc


def test_change_coupling_hubs_section() -> None:
    city = _city()
    doc = build_okf_bundle(city)["hotspots.md"]
    assert "# Change-coupling hubs" not in doc
    assert "50 commits, plus oversized source files." in doc  # frontmatter lists real sections
    city.commit_files = [
        ["src/app.py", "src/util.py"],
        ["src/app.py", "src/util.py"],
    ]
    doc = build_okf_bundle(city)["hotspots.md"]
    assert "# Change-coupling hubs" in doc
    assert "plus change-coupling hubs and oversized source files." in doc
    assert "| `src/app.py` | 1 | 2 | `src/util.py` (2) |" in doc


def test_hotspots_ranked_and_flagged() -> None:
    doc = build_okf_bundle(_city())["hotspots.md"]
    ranked_rows = [line for line in doc.splitlines() if line.startswith("| `")]
    assert ranked_rows[0].startswith("| `src/app.py` | 120 |")
    assert "removed at HEAD" in doc  # gone/old.py is not in the tree
    assert "# Oversized source files" in doc  # app.py is over the 40 KB threshold


def test_default_bundle_is_flat() -> None:
    bundle = build_okf_bundle(_city())
    assert set(bundle) == {"index.md", "repository.md", "hotspots.md", "districts/index.md"}
    table = bundle["districts/index.md"]
    assert "| district | files | bytes | max depth | recent churn | largest file |" in table
    assert "| src | 2 (40%) | 49.3 KB | 1 | 120 lines (90%) | `src/app.py` (48.8 KB) |" in table
    assert "[src](src.md)" not in table  # no district docs to link to
    linked = build_okf_bundle(_city(), inventory=True)["districts/index.md"]
    assert "| [src](src.md) | 2 (40%)" in linked


def test_district_files_inventory() -> None:
    doc = build_okf_bundle(_city(), inventory=True)["districts/src.md"]
    assert "# Files" in doc
    assert "Complete inventory: 2 files." in doc
    assert "**`src/`**" in doc
    assert "- `app.py` (48.8 KB)" in doc
    assert "- `util.py` (500 B)" in doc


def test_district_files_inventory_truncates() -> None:
    files = [SourceFile(f"big/f{i:04}.py", size=10) for i in range(250)]
    data = CityData(repo="o/r", files=files)
    doc = build_okf_bundle(data, inventory=True)["districts/big.md"]
    assert "First 200 of 250 files, sorted by path." in doc
    assert "- `f0199.py` (10 B)" in doc
    assert "`f0200.py`" not in doc
    assert "(50 more not shown; run `git ls-tree -r HEAD` for the full tree.)" in doc


def test_districts_follow_banner_cut() -> None:
    files = (
        [SourceFile(f"pkg/core/c{i}.py", size=100) for i in range(5)]
        + [SourceFile(f"pkg/io/i{i}.py", size=100) for i in range(5)]
        + [SourceFile(f"pkg/loose{i}.py", size=100) for i in range(4)]
        + [SourceFile("docs/intro.md", size=50)]
    )
    bundle = build_okf_bundle(CityData(repo="o/r", files=files), inventory=True)
    assert {"districts/pkg-core.md", "districts/pkg-io.md", "districts/pkg.md"} <= bundle.keys()
    assert "| largest district | pkg/core, 33% of files |" in bundle["repository.md"]


def test_links_are_relative() -> None:
    for inventory in (False, True):
        bundle = build_okf_bundle(_city(), inventory=inventory)
        for path, doc in bundle.items():
            assert "](/" not in doc, f"{path} has a root-absolute link"
    bundle = build_okf_bundle(_city(), inventory=True)
    assert "[repository overview](../repository.md)" in bundle["districts/src.md"]
    assert "[src](src.md)" in bundle["districts/index.md"]


def test_lockfile_churn_counts_like_any_other_file() -> None:
    files = [SourceFile("uv.lock", size=100), SourceFile("src/app.py", size=100)]
    data = CityData(repo="o/r", files=files, touches={"uv.lock": 999, "src/app.py": 5})
    bundle = build_okf_bundle(data)
    doc = bundle["hotspots.md"]
    assert "| `uv.lock` | 999 |" in doc
    assert "| `src/app.py` | 5 |" in doc
    assert "excluded" not in doc
    # District churn shares include it (999 of 1004), matching the banner's lit windows.
    table = bundle["districts/index.md"]
    assert "| 999 lines (100%) | `uv.lock` (100 B) |" in table
    assert "| 5 lines (0%) | `src/app.py` (100 B) |" in table


def test_cap_overflow_district_is_flagged() -> None:
    files = [SourceFile(f"pkg/sub{i:02}/f.py", size=100) for i in range(20)]
    bundle = build_okf_bundle(CityData(repo="o/r", files=files), inventory=True)
    overflow = bundle["districts/pkg.md"]
    assert "no banner label" in overflow
    assert "district cap" in overflow
    assert "no banner label" not in bundle["districts/pkg-sub00.md"]
    # The fingerprint points at a banner label, never the overflow group.
    assert "| largest district | pkg/sub00, 5% of files |" in bundle["repository.md"]


def test_skill_doc_is_opt_in() -> None:
    assert "SKILL.md" not in build_okf_bundle(_city())
    doc = build_okf_bundle(_city(), skill=True)["SKILL.md"]
    front = _frontmatter_of(doc)
    assert 'name: "repo-map"' in front
    assert "Structural map of owner/repo" in front
    assert "abc1234" not in front  # descriptions load every session; keep them sha-stable
    assert "[repository.md](repository.md)" in doc
    assert "[hotspots.md](hotspots.md)" in doc
    assert "[the README](https://github.com/owner/repo#readme)" in doc


def test_skill_name_slug_for_local_paths() -> None:
    data = CityData(repo="My_Repo.py", files=[SourceFile("a.py", size=1)])
    front = _frontmatter_of(build_okf_bundle(data, skill=True)["SKILL.md"])
    assert 'name: "my-repo-py-map"' in front
    assert "the README at the repository root" in build_okf_bundle(data, skill=True)["SKILL.md"]


def test_bundle_is_deterministic() -> None:
    assert build_okf_bundle(_city()) == build_okf_bundle(_city())


def test_write_clears_stale_districts(tmp_path: Path) -> None:
    stale = tmp_path / "districts" / "old-name.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("---\ntype: Directory\n---\n", encoding="utf-8")

    count = write_okf_bundle(_city(), tmp_path)

    assert count == len(list(tmp_path.rglob("*.md")))
    assert not stale.exists()
    assert (tmp_path / "repository.md").exists()


def test_empty_repo_does_not_crash() -> None:
    bundle = build_okf_bundle(CityData(repo="o/r"))
    assert "repository.md" in bundle
    assert "districts/index.md" not in bundle
