"""Change-coupling hubs: files that keep landing in the same commits."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

from repoglyph.metrics.base import Finding, code_cell
from repoglyph.models import CityData

__all__ = ["CHANGE_COUPLING"]

#: A sweeping commit (reformat, mass rename) couples everything it touches; skip it.
_BULK_COMMIT_FILES = 30
#: A pair must share at least this many commits to count as coupled.
_MIN_SHARED = 2
_ROW_LIMIT = 15
_LINK_LIMIT = 3


def _change_coupling(data: CityData) -> list[tuple[str, ...]]:
    present = {f.path for f in data.files}
    pairs: Counter[tuple[str, str]] = Counter()
    for commit in data.commit_files:
        members = sorted({p for p in commit if p in present})
        if len(members) < 2 or len(members) > _BULK_COMMIT_FILES:
            continue
        pairs.update(combinations(members, 2))

    links: dict[str, Counter[str]] = {}
    for (a, b), shared in pairs.items():
        if shared < _MIN_SHARED:
            continue
        links.setdefault(a, Counter())[b] = shared
        links.setdefault(b, Counter())[a] = shared

    ranked = sorted(links.items(), key=lambda kv: (-len(kv[1]), -sum(kv[1].values()), kv[0]))
    rows = []
    for path, partners in ranked[:_ROW_LIMIT]:
        strongest = sorted(partners.items(), key=lambda item: (-item[1], item[0]))
        rows.append(
            (
                code_cell(path),
                str(len(partners)),
                f"{sum(partners.values()):,}",
                ", ".join(f"{code_cell(p)} ({n})" for p, n in strongest[:_LINK_LIMIT]),
            )
        )
    return rows


CHANGE_COUPLING = Finding(
    key="change_coupling",
    title="Change-coupling hubs",
    blurb=(
        f"Files that repeatedly change in the same commits, ranked by how many partners "
        f"they co-change with (pairs sharing under {_MIN_SHARED} commits and bulk commits "
        f"touching over {_BULK_COMMIT_FILES} files are ignored). Broad coupling marks a "
        "structural hub; unexpected coupling marks a candidate for decoupling."
    ),
    columns=("file", "coupled files", "co-changes", "strongest links"),
    compute=_change_coupling,
)
