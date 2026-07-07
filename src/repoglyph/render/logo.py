"""The repoglyph mark: an iso cube whose top edge detours into a commit tail."""

from __future__ import annotations

import math
from typing import TypedDict

__all__ = ["SOLID_LOGO", "LogoOpts", "render_logo"]

# --- colours (tweak freely) -------------------------------------------------
_STROKE = "#5ef2d0"  # cube wireframe
_NODE = "#ffd166"  # commit dots
_KEYLINE = "#0a0f0d"  # thin dark outline for light-ground legibility
_CUBE_FILL = "#0d1c17"  # dark-green cube body, so the mark keeps its own dark ground


class LogoOpts(TypedDict, total=False):
    """Optional overrides for :func:`render_logo`, unpackable via ``**``."""

    stroke: str
    node: str
    keyline: str
    cube_fill: str
    base_nudge: bool


# The "solid" treatment used on the site chrome (favicon + OG card): dark cube
# walls, keylined, tail base tucked inside. Opt-in; the banner logo passes no
# opts and stays a plain wireframe (byte-identical goldens).
SOLID_LOGO: LogoOpts = {"keyline": _KEYLINE, "cube_fill": _CUBE_FILL, "base_nudge": True}

# --- shape knobs ------------------------------------------------------------
_CUBE_SCALE = 0.90  # cube size relative to r (1.0 = fills r)
_TAIL_REACH = 1.20  # how far the commit tail trails past the cube
_OUT_W = 1.0  # keyline half-extension past each edge
_RING_W = 1.3  # dark ring width on the node dots
_BASE_DX = -0.05  # tail-base nudge (fractions of r): left …
_BASE_DY = -0.03  # … and up, so it sits more inside the box


def render_logo(
    cx: float,
    cy: float,
    r: float,
    *,
    stroke: str = _STROKE,
    node: str = _NODE,
    keyline: str | None = None,
    cube_fill: str | None = None,
    base_nudge: bool = False,
) -> str:
    """Render the mark centred at ``(cx, cy)`` with outer radius ``r``.

    ``keyline`` (color) draws a dark outline behind every stroke + a ring on the
    nodes and shrinks the shapes so the outlined mark keeps the original
    silhouette; ``cube_fill`` (color) fills the cube body; ``base_nudge`` tucks the
    commit node / tail base inward. All default off, so ``render_logo(x, y, r)`` is
    the plain wireframe (unchanged for callers that pass no opts).
    """
    keyed = keyline is not None
    ring_half = _RING_W / 2

    def fmt(p: tuple[float, float]) -> str:
        return f"{p[0]:.1f},{p[1]:.1f}"

    def seg(a: tuple[float, float], b: tuple[float, float]) -> str:
        return f"M{fmt(a)}L{fmt(b)}"

    # a centered keyline extends _OUT_W past every edge; pull the cube in by that
    # much (and the dots by the ring's half-width) so the silhouette is unchanged.
    e = r * 0.7 * _CUBE_SCALE - (_OUT_W if keyed else 0.0)
    h = 0.866 * e
    sw = max(1.1, r * 0.11)
    rad = max(1.5, r * 0.15)

    # isometric cube corners (top, upper-right, lower-right, bottom, lower-left,
    # upper-left, near-centre).
    top = (cx, cy - e)
    ur = (cx + h, cy - 0.5 * e)
    lr = (cx + h, cy + 0.5 * e)
    bot = (cx, cy + e)
    ll = (cx - h, cy + 0.5 * e)
    ul = (cx - h, cy - 0.5 * e)
    ctr = (cx, cy)

    # open hexagon: every outer edge except top->upper-right (that one detours).
    hexagon = " ".join(fmt(p) for p in (ur, lr, bot, ll, ul, top))
    spokes = seg(ctr, ur) + seg(ctr, bot) + seg(ctr, ul)

    # the detour: top -> kinked commit node -> upper-right.
    off = e * 0.371
    mx, my = (top[0] + ur[0]) / 2, (top[1] + ur[1]) / 2
    dx, dy = ur[0] - top[0], ur[1] - top[1]
    length = math.hypot(dx, dy) or 1.0
    m = (
        mx - dy / length * off + (_BASE_DX * r if base_nudge else 0.0),
        my + dx / length * off + (_BASE_DY * r if base_nudge else 0.0),
    )
    detour = seg(top, m) + seg(m, ur)

    # the commit tail trailing from the node (a gentle bend).
    a = (m[0] + _TAIL_REACH * 0.227 * r, m[1] - _TAIL_REACH * 0.22 * r)
    b = (m[0] + _TAIL_REACH * 0.547 * r, m[1] - _TAIL_REACH * 0.30 * r)
    tail = seg(m, a) + seg(a, b)

    def strokes(color: str, width: float) -> str:
        return (
            f'<g fill="none" stroke="{color}" stroke-linejoin="round" stroke-linecap="round">'
            f'<polyline points="{hexagon}" fill="none" stroke-width="{width:.1f}" opacity="0.92"/>'
            f'<path d="{spokes}" stroke-width="{width:.1f}" opacity="0.78"/>'
            f'<path d="{detour}" stroke-width="{width:.1f}" opacity="0.92"/>'
            f'<path d="{tail}" stroke-width="{width:.1f}" opacity="0.9"/>'
            "</g>"
        )

    parts: list[str] = []
    if keyed:
        parts.append(strokes(keyline, sw + 2 * _OUT_W))  # dark keyline behind
    if cube_fill:
        parts.append(f'<polygon points="{hexagon}" fill="{cube_fill}"/>')  # dark cube body
    parts.append(strokes(stroke, sw))  # wireframe on top

    ring = f' stroke="{keyline}" stroke-width="{_RING_W:.1f}"' if keyed else ""

    def dot(p: tuple[float, float], rr: float) -> str:
        rv = max(0.8, rr - ring_half) if keyed else rr
        return f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{rv:.1f}" fill="{node}"{ring}/>'

    parts.append(dot(m, rad))
    parts.append(dot(a, rad * 0.66))
    parts.append(dot(b, rad * 0.8))
    return "".join(parts)
