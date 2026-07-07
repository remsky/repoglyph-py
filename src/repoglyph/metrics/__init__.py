"""Structural metrics: the fingerprint stats and the finding tables.

Adding a metric is one module plus one registry line here:

* a ``Stat`` is one row of the fingerprint table (label + formatted value);
* a ``Finding`` is one ranked-table section (heading, blurb, rows).

Registered metrics surface automatically in the OKF bundle (``repository.md``
for stats, ``hotspots.md`` for findings). The banner HUD is deliberately not
registry-driven: it keeps its hand-picked set in ``render/overlay.py`` so new
metrics never disturb the panel layout or the golden snapshots.
"""

from repoglyph.metrics.base import Finding, Stat, code_cell, fmt_bytes
from repoglyph.metrics.core import (
    OVERSIZED_FILE_BYTES,
    STATS,
    RepoMetrics,
    compute_metrics,
)
from repoglyph.metrics.oversized import OVERSIZED_FILES

__all__ = [
    "FINDINGS",
    "OVERSIZED_FILE_BYTES",
    "STATS",
    "Finding",
    "RepoMetrics",
    "Stat",
    "code_cell",
    "compute_metrics",
    "fmt_bytes",
]

#: Every registered finding, in display order.
FINDINGS: tuple[Finding, ...] = (OVERSIZED_FILES,)
