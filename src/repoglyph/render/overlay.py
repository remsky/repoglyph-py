"""Render the HUD: the left fingerprint panel and the bottom-right color legend."""

from __future__ import annotations

import html
import math

from repoglyph.geometry import PANEL_WIDTH, BannerLayout
from repoglyph.metrics import RepoMetrics
from repoglyph.models import sha_label
from repoglyph.palette import CATEGORIES, CATEGORY_COLORS, Category
from repoglyph.palettes import DARK_CHROME, Chrome
from repoglyph.render.logo import render_logo
from repoglyph.render.svg import text

__all__ = ["render_panel", "render_legend"]

type _Colors = dict[Category, tuple[str, str, str]]

#: Title font: full size, and the floor it shrinks to before wrapping at the owner slash.
_TITLE_SIZE = 22.0
_TITLE_FLOOR = 13.0
#: Width above which a district name shown in a stat line is middle-elided.
_PANEL_PATH_MAX = 30


def _format_count(n: int) -> str:
    """Display a contributor count, coarsened for larger repos."""
    if n < 100:
        return str(n)
    if n < 1000:
        return f"{(n // 10) * 10}+"
    return f"{(n // 100) / 10:g}k+"


def _shrink_title_line(name: str, ts: float) -> tuple[str, float]:
    """Fit one title line to the panel column: shrink, then trail-elide at the floor."""
    max_w = PANEL_WIDTH - 4
    full = _TITLE_SIZE * ts
    floor = _TITLE_FLOOR * ts
    if 0.6 * full * len(name) <= max_w:
        return name, full
    size = math.floor(max_w / (0.6 * len(name)))
    if size >= floor:
        return name, size
    max_chars = math.floor(max_w / (0.6 * floor))
    if len(name) <= max_chars:
        return name, floor
    return f"{name[: max(1, max_chars - 1)]}…", floor


def _fit_title(name: str, ts: float) -> list[tuple[str, float]]:
    """Fit the repo title: one line when it fits, else wrap ``owner/`` above the repo."""
    line, size = _shrink_title_line(name, ts)
    if line == name:
        return [(name, size)]
    slash = name.rfind("/")
    if slash <= 0:
        return [(line, size)]
    return [
        _shrink_title_line(name[: slash + 1], ts),
        _shrink_title_line(name[slash + 1 :], ts),
    ]


def _shorten_label(path: str) -> str:
    """Middle-elide a deep district path so a stat line stays in the column."""
    if len(path) <= _PANEL_PATH_MAX:
        return path
    segs = path.split("/")
    if len(segs) <= 2:
        return path
    return f"{segs[0]}/…/{segs[-1]}"


def _clamp_width(content: str, size: float, indent: float = 0) -> str:
    """Hard backstop: trailing-elide *content* so it can't overflow the column."""
    max_chars = math.floor((PANEL_WIDTH - indent - 4) / (0.6 * size))
    if len(content) <= max_chars:
        return content
    if max_chars <= 1:
        return "…"
    return f"{content[: max_chars - 1]}…"


def _fit_line(content: str, base: float, floor: float = 10.5) -> float:
    """Shrink one stat line's font (down to *floor*) so it fits on one row."""
    max_w = PANEL_WIDTH - 8
    if 0.6 * base * len(content) <= max_w:
        return base
    return max(floor, max_w / (0.6 * len(content)))


def render_panel(
    repo: str,
    commit_window: int,
    touches: dict[str, int],
    metrics: RepoMetrics,
    banner: BannerLayout,
    chrome: Chrome,
    *,
    truncated: bool = False,
    ts: float = 1.0,
    head_sha: str | None = None,
) -> str:
    """Render the left-hand fingerprint readout, anchored to the top-left.

    ``ts`` scales every font size and the vertical step in lockstep. The optional
    ``head_sha`` prefixes the subtitle line ("<sha> · structural fingerprint"),
    which shrinks to fit the panel column on one line, never spilling.
    """
    left = banner.pad
    title_lines = _fit_title(repo, ts)
    # A wrapped slug stacks "owner/" as a small eyebrow line over the repo name.
    if len(title_lines) == 1:
        title_ys = [banner.pad + 22 * ts]
    else:
        title_ys = [banner.pad + 14 * ts, banner.pad + 38 * ts]
    sub_y = title_ys[-1] + 18 * ts
    short_sha = sha_label(str(head_sha)) if head_sha else None
    stats_y = sub_y + 24 * ts

    counts = f"{metrics.file_count} files · {metrics.dir_count} dirs · depth {metrics.max_depth}"
    rows: list[dict] = [{"kind": "main", "text": counts, "size": _fit_line(counts, 14 * ts)}]

    largest_pct = round(metrics.largest_district_share * 100)
    rows.append({"kind": "main", "text": f"most files · {largest_pct}%"})
    rows.append({"kind": "sub", "text": _shorten_label(metrics.largest_district or ".root")})

    if metrics.active_district:
        active_pct = round(metrics.active_district_share * 100)
        rows.append({"kind": "main", "text": f"most active · {active_pct}%"})
        rows.append({"kind": "sub", "text": _shorten_label(metrics.active_district)})
    if metrics.contributor_count > 0:
        rows.append(
            {"kind": "main", "text": f"{_format_count(metrics.contributor_count)} contributors"}
        )

    sub_plain = f"structural fingerprint · {short_sha}" if short_sha else "structural fingerprint"
    sub_size = _fit_line(sub_plain, 12 * ts)
    sub_clamped = _clamp_width(sub_plain, sub_size)
    if short_sha and sub_clamped == sub_plain:
        sha_escaped = html.escape(short_sha)
        sub_content = f'structural fingerprint · <tspan fill="{chrome.muted}">{sha_escaped}</tspan>'
    else:
        sub_content = html.escape(sub_clamped)
    parts = []
    if len(title_lines) > 1:
        owner_text, owner_size = title_lines[0]
        parts.append(
            text(
                left,
                title_ys[0],
                html.escape(owner_text),
                fill=chrome.muted,
                size=min(owner_size, _TITLE_FLOOR * ts),
                extra='font-weight="600"',
            )
        )
    name_text, name_size = title_lines[-1]
    parts.append(
        text(
            left,
            title_ys[-1],
            html.escape(name_text),
            fill=chrome.ink,
            size=name_size,
            extra='font-weight="700"',
        )
    )
    parts.append(
        text(
            left,
            sub_y,
            sub_content,
            fill=chrome.accent,
            size=sub_size,
        )
    )

    y = stats_y
    for i, row in enumerate(rows):
        if row["kind"] == "sub":
            parts.append(
                text(
                    left + 12 * ts,
                    y,
                    html.escape(_clamp_width(row["text"], 12.5 * ts, 12 * ts)),
                    fill=chrome.muted,
                    size=12.5 * ts,
                )
            )
            y += 26 * ts
        else:
            size = row.get("size") or 14 * ts
            parts.append(
                text(
                    left,
                    y,
                    html.escape(_clamp_width(row["text"], size)),
                    fill=chrome.stat,
                    size=size,
                )
            )
            nxt = rows[i + 1] if i + 1 < len(rows) else None
            gap = 19 if nxt and nxt["kind"] == "sub" else 24
            y += gap * ts

    # Footnote (swatch + window line) is fine print: cap its scale so the long
    # static strings stay in the column even when the headline stats keep growing.
    nts = min(ts, 1.35)
    note_y = y + 16 * ts
    note_indent = 20 * nts
    edge = f' stroke="{chrome.swatch_stroke}"' if chrome.swatch_stroke != "none" else ""
    sw = round(13 * nts)
    parts.append(
        f'<rect x="{left}" y="{round(note_y - 12 * nts)}" width="{sw}" height="{sw}"'
        f' fill="#fff2c2" rx="{max(1, round(2 * nts))}"{edge}/>'
    )
    parts.append(
        text(
            left + note_indent,
            note_y,
            _clamp_width("light = files touched in", 12 * nts, note_indent),
            fill=chrome.muted,
            size=12 * nts,
        )
    )
    window_note = f"last {commit_window} commits ({len(touches)}/{metrics.file_count})" + (
        " · partial" if truncated else ""
    )
    parts.append(
        text(
            left + note_indent,
            note_y + 18 * nts,
            _clamp_width(window_note, 12 * nts, note_indent),
            fill=chrome.muted,
            size=12 * nts,
        )
    )

    # Brand signature, bottom-left corner; mirrors the legend on the opposite side.
    sig_y = banner.legend_y
    sig_r = 8
    parts.append(render_logo(left + sig_r, sig_y - 4, sig_r, stroke=chrome.accent))
    parts.append(text(left + 2 * sig_r + 6, sig_y, "repoglyph.net", fill=chrome.accent, size=14))

    return "".join(parts)


def render_legend(
    banner: BannerLayout, *, colors: _Colors = CATEGORY_COLORS, chrome: Chrome = DARK_CHROME
) -> str:
    """Render the color legend as a horizontal row in the reserved bottom strip."""
    y = banner.legend_y
    parts: list[str] = []
    cursor = banner.legend_x
    edge = f' stroke="{chrome.swatch_stroke}"' if chrome.swatch_stroke != "none" else ""
    for category, label in CATEGORIES:
        swatch = colors[category][0]
        parts.append(
            f'<rect x="{cursor:.0f}" y="{y - 11:.0f}" width="13" height="13" '
            f'fill="{swatch}" rx="2"{edge}/>'
        )
        parts.append(text(cursor + 19, y, label, fill=chrome.muted, size=14))
        cursor += 76
    return "".join(parts)
