"""Export gathered repo data as an Open Knowledge Format (OKF) bundle.

OKF (github.com/GoogleCloudPlatform/knowledge-catalog) is a vendor-neutral
convention for handing curated context to AI agents: a directory of markdown
files, one concept per file, each with YAML frontmatter whose only required
field is ``type``. This module renders ``CityData`` into such a bundle:

    index.md            directory listing (reserved name, no frontmatter)
    repository.md       fingerprint metrics + district overview
    hotspots.md         files ranked by recent churn, oversized-file watchlist
    districts/<d>.md    one concept per top-level directory, with full inventory

Output is deterministic for a given ``CityData`` (no wall-clock timestamps),
so regenerating without new commits is a no-op diff.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from repoglyph import __version__
from repoglyph.metrics import (
    FINDINGS,
    STATS,
    RepoMetrics,
    code_cell,
    compute_metrics,
    fmt_bytes,
)
from repoglyph.models import CityData, SourceFile, group_by_district
from repoglyph.palette import CATEGORIES, categorize

__all__ = ["build_okf_bundle", "write_okf_bundle"]

logger = logging.getLogger(__name__)

#: Filenames the OKF spec reserves for structural documents, never concepts.
_RESERVED_NAMES = frozenset({"index", "log"})

#: Row budgets for the ranked tables.
_HOTSPOT_LIMIT = 20
_DISTRICT_FILE_LIMIT = 10

#: Cap on the per-district file inventory, so a monorepo district cannot
#: produce a multi-thousand-line document. Truncation is always stated.
_DISTRICT_LISTING_LIMIT = 200

_SLUG_RE = re.compile(r"[^a-z0-9._-]+")
_GITHUB_SLUG_RE = re.compile(r"^[\w.-]+/[\w.-]+$")


# --------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------
def build_okf_bundle(data: CityData, metrics: RepoMetrics | None = None) -> dict[str, str]:
    """Render *data* into a bundle: relative posix path -> markdown content."""
    if metrics is None:
        metrics = compute_metrics(data)

    total_churn = sum(data.touches.values())
    districts = group_by_district(data.files)
    names = sorted(districts, key=lambda name: (-len(districts[name]), name))
    slugs = _district_slugs(names)
    rows = [
        _DistrictRow(
            name=name,
            slug=slugs[name],
            files=districts[name],
            churn=sum(count for path, count in data.touches.items() if _district(path) == name),
            total_churn=total_churn,
        )
        for name in names
    ]

    bundle = {
        "repository.md": _repository_doc(data, metrics, rows),
        "hotspots.md": _hotspots_doc(data, rows),
        "index.md": _root_index(data, rows),
    }
    for row in rows:
        bundle[f"districts/{row.slug}.md"] = _district_doc(data, row)
    if rows:
        bundle["districts/index.md"] = _district_index(rows)
    return bundle


def write_okf_bundle(
    data: CityData,
    out_dir: Path,
    metrics: RepoMetrics | None = None,
) -> int:
    """Write the bundle under *out_dir* and return the number of documents.

    ``districts/*.md`` is cleared first so a renamed top-level directory does
    not leave a stale concept behind; treat *out_dir* as generated output.
    """
    bundle = build_okf_bundle(data, metrics)
    stale = out_dir / "districts"
    if stale.is_dir():
        for path in stale.glob("*.md"):
            path.unlink()
    for rel, content in bundle.items():
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    logger.info("wrote OKF bundle (%d documents) to %s", len(bundle), out_dir)
    return len(bundle)


# --------------------------------------------------------------------------
# per-district working row
# --------------------------------------------------------------------------
class _DistrictRow:
    """A drawn district plus the aggregates every document needs."""

    def __init__(
        self,
        *,
        name: str,
        slug: str,
        files: list[SourceFile],
        churn: int,
        total_churn: int,
    ) -> None:
        self.name = name
        self.slug = slug
        self.files = files
        self.bytes = sum(file.size for file in files)
        self.churn = churn
        self.churn_share = churn / total_churn if total_churn else 0.0

    @property
    def link(self) -> str:
        return f"[{self.name}](/districts/{self.slug}.md)"

    def blurb(self, file_count: int) -> str:
        share = len(self.files) / file_count if file_count else 0.0
        parts = [f"{_n_files(len(self.files))} ({share:.0%})", fmt_bytes(self.bytes)]
        if self.churn:
            parts.append(f"{self.churn_share:.0%} of recent churn")
        return ", ".join(parts)


# --------------------------------------------------------------------------
# documents
# --------------------------------------------------------------------------
def _repository_doc(data: CityData, metrics: RepoMetrics, rows: list[_DistrictRow]) -> str:
    front = _frontmatter(
        type="Repository",
        title=data.repo,
        description=(
            f"Structural fingerprint of {data.repo}: {metrics.file_count} files in "
            f"{metrics.dir_count} directories, activity from the last "
            f"{data.commit_window} commits."
        ),
        resource=(f"https://github.com/{data.repo}" if _GITHUB_SLUG_RE.match(data.repo) else None),
        tags=["repoglyph", "fingerprint"],
        head_sha=data.head_sha,
        commit_window=data.commit_window,
        generator=f"repoglyph {__version__}",
    )

    fingerprint = [
        (stat.label, value) for stat in STATS if (value := stat.compute(data, metrics)) is not None
    ]

    counts = {key: [0, 0] for key, _ in CATEGORIES}
    for file in data.files:
        entry = counts[categorize(file.path)]
        entry[0] += 1
        entry[1] += file.size
    composition = [
        (label, f"{count:,}", fmt_bytes(size))
        for (key, label) in CATEGORIES
        for count, size in [counts[key]]
        if count
    ]

    lines = [front, "", "# Fingerprint", "", "| metric | value |", "| --- | --- |"]
    lines += [f"| {key} | {value} |" for key, value in fingerprint]
    if composition:
        lines += ["", "# Composition", "", "| category | files | bytes |", "| --- | --- | --- |"]
        lines += [f"| {label} | {count} | {size} |" for label, count, size in composition]
    if rows:
        lines += ["", "# Districts", ""]
        lines += [f"* {row.link} - {row.blurb(metrics.file_count)}" for row in rows]
    lines += [
        "",
        "# Notes",
        "",
        f"- Activity covers only the last {data.commit_window} commits"
        + (f" at `{data.head_sha[:9]}`" if data.head_sha else "")
        + "; an untouched file is dormant in that window, not necessarily dead.",
        "- Sizes are blob bytes at HEAD, not lines of code.",
        "- Districts are top-level directories: they show organization, not import coupling.",
        "",
        "Ranked churn lives in [hotspots](/hotspots.md).",
        "",
    ]
    return "\n".join(lines)


def _hotspots_doc(data: CityData, rows: list[_DistrictRow]) -> str:
    front = _frontmatter(
        type="Report",
        title="Hotspots",
        description=(
            f"Files ranked by line churn over the last {data.commit_window} commits, "
            "plus oversized source files."
        ),
        tags=["repoglyph", "churn"],
    )
    sizes = {file.path: file.size for file in data.files}
    links = {row.name: row.link for row in rows}
    ranked = sorted(data.touches.items(), key=lambda item: (-item[1], item[0]))

    lines = [front, "", "# Ranked by recent churn", ""]
    if ranked:
        lines += ["| file | lines changed | size at HEAD | district |", "| --- | --- | --- | --- |"]
        for path, churn in ranked[:_HOTSPOT_LIMIT]:
            size = fmt_bytes(sizes[path]) if path in sizes else "removed at HEAD"
            district = links.get(_district(path), _district(path))
            lines.append(f"| {code_cell(path)} | {churn:,} | {size} | {district} |")
        if len(ranked) > _HOTSPOT_LIMIT:
            lines += ["", f"({len(ranked) - _HOTSPOT_LIMIT} more touched files not shown.)"]
        if data.touch_truncated:
            lines += [
                "",
                "The churn sample is a truncated slice of the window; treat ranks as approximate.",
            ]
    else:
        lines.append("No commit activity was sampled.")

    for finding in FINDINGS:
        found = finding.compute(data)
        if not found:
            continue
        lines += [
            "",
            f"# {finding.title}",
            "",
            finding.blurb,
            "",
            "| " + " | ".join(finding.columns) + " |",
            "|" + " --- |" * len(finding.columns),
        ]
        lines += ["| " + " | ".join(cells) + " |" for cells in found]
    lines += ["", "Context: [repository overview](/repository.md).", ""]
    return "\n".join(lines)


def _district_doc(data: CityData, row: _DistrictRow) -> str:
    is_root = row.name == ".root"
    front = _frontmatter(
        type="Directory",
        title=row.name,
        description=(
            "Files at the repository root."
            if is_root
            else f"Top-level directory `{row.name}/`: {_n_files(len(row.files))}, "
            f"{fmt_bytes(row.bytes)}."
        ),
        tags=["repoglyph", "district"],
        files=len(row.files),
        bytes=row.bytes,
    )

    file_share = len(row.files) / len(data.files) if data.files else 0.0
    stats = [
        ("files", f"{len(row.files):,} ({file_share:.0%} of the repo)"),
        ("bytes", fmt_bytes(row.bytes)),
        ("max depth", str(max((f.depth for f in row.files), default=0))),
        ("recent churn", f"{row.churn:,} lines ({row.churn_share:.0%} of the window)"),
    ]
    lines = [front, "", "# Stats", "", "| metric | value |", "| --- | --- |"]
    lines += [f"| {key} | {value} |" for key, value in stats]

    largest = sorted(row.files, key=lambda f: (-f.size, f.path))[:_DISTRICT_FILE_LIMIT]
    lines += ["", "# Largest files", "", "| file | size | category |", "| --- | --- | --- |"]
    lines += [
        f"| {code_cell(f.path)} | {fmt_bytes(f.size)} | {categorize(f.path)} |" for f in largest
    ]

    active = sorted(
        ((path, count) for path, count in data.touches.items() if _district(path) == row.name),
        key=lambda item: (-item[1], item[0]),
    )[:_DISTRICT_FILE_LIMIT]
    if active:
        lines += ["", "# Recently active", "", "| file | lines changed |", "| --- | --- |"]
        lines += [f"| {code_cell(path)} | {count:,} |" for path, count in active]

    lines += _files_section(row)
    lines += ["", "Context: [repository overview](/repository.md).", ""]
    return "\n".join(lines)


def _files_section(row: _DistrictRow) -> list[str]:
    """The full file inventory of a district, grouped by directory."""
    ordered = sorted(row.files, key=lambda f: f.path)
    listed = ordered[:_DISTRICT_LISTING_LIMIT]
    truncated = len(ordered) - len(listed)

    lines = ["", "# Files", ""]
    if truncated:
        lines.append(f"First {len(listed):,} of {_n_files(len(ordered))}, sorted by path.")
    else:
        lines.append(f"Complete inventory: {_n_files(len(ordered))}.")

    groups: dict[str, list[SourceFile]] = {}
    for file in listed:
        directory, _, _ = file.path.rpartition("/")
        groups.setdefault(directory, []).append(file)
    for directory in sorted(groups):
        label = f"**`{directory}/`**" if directory else "**repository root**"
        lines += ["", label, ""]
        for file in groups[directory]:
            _, _, name = file.path.rpartition("/")
            lines.append(f"- `{name}` ({fmt_bytes(file.size)})")

    if truncated:
        note = f"({truncated:,} more not shown; run `git ls-tree -r HEAD` for the full tree.)"
        lines += ["", note]
    return lines


def _root_index(data: CityData, rows: list[_DistrictRow]) -> str:
    lines = [
        f"# {data.repo}",
        "",
        f"Structural knowledge about `{data.repo}`, generated by repoglyph from the "
        f"git tree and the last {data.commit_window} commits.",
        "",
        "* [Repository](/repository.md) - fingerprint metrics and district overview",
        "* [Hotspots](/hotspots.md) - files ranked by recent churn",
    ]
    if rows:
        lines += ["", "# Districts", ""]
        lines += [f"* {row.link} - {row.blurb(len(data.files))}" for row in rows]
    lines.append("")
    return "\n".join(lines)


def _district_index(rows: list[_DistrictRow]) -> str:
    lines = ["# Districts", ""]
    lines += [f"* {row.link} - {_n_files(len(row.files))}, {fmt_bytes(row.bytes)}" for row in rows]
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# formatting helpers
# --------------------------------------------------------------------------
def _frontmatter(**fields: object) -> str:
    """Serialize *fields* to a YAML frontmatter block, skipping ``None`` values.

    Strings are JSON-encoded, which is a valid YAML double-quoted scalar.
    """
    lines = ["---"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key}: [{', '.join(json.dumps(item) for item in value)}]")
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {json.dumps(value)}")
    lines.append("---")
    return "\n".join(lines)


def _district(path: str) -> str:
    return SourceFile(path).district


def _district_slugs(names: list[str]) -> dict[str, str]:
    """Map district names to unique, filesystem- and spec-safe file stems."""
    slugs: dict[str, str] = {}
    used: set[str] = set()
    for name in names:
        base = _SLUG_RE.sub("-", name.lower()).strip("-.") or "district"
        if base in _RESERVED_NAMES:
            base += "-district"
        slug, n = base, 2
        while slug in used:
            slug = f"{base}-{n}"
            n += 1
        used.add(slug)
        slugs[name] = slug
    return slugs


def _n_files(count: int) -> str:
    return f"{count:,} file" + ("" if count == 1 else "s")
