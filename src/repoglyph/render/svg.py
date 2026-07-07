"""Low-level SVG string helpers and the outer document scaffold."""

from __future__ import annotations

from repoglyph.geometry import BannerLayout
from repoglyph.palettes import Chrome
from repoglyph.render.typeface import FONT_FAMILY, font_face_css

__all__ = ["MONO", "text", "assemble_document"]

#: Document-wide font-family: bundled Monaspace Xenon then a system-mono fallback.
MONO = f"font-family=\"'{FONT_FAMILY}', ui-monospace, Menlo, monospace\""


def _gradients(chrome: Chrome) -> str:
    """Sky + glow gradient defs from the palette's chrome (left open for clip-paths)."""
    top, mid, bottom = chrome.bg
    return (
        '<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{top}"/>'
        f'<stop offset="0.55" stop-color="{mid}"/>'
        f'<stop offset="1" stop-color="{bottom}"/></linearGradient>'
        '<radialGradient id="glow" cx="0.6" cy="0.8" r="0.7">'
        f'<stop offset="0" stop-color="{chrome.glow}" stop-opacity="{chrome.glow_opacity}"/>'
        f'<stop offset="1" stop-color="{chrome.glow}" stop-opacity="0"/></radialGradient>'
    )


def text(
    x: float,
    y: float,
    content: str,
    *,
    fill: str,
    size: float,
    extra: str = "",
) -> str:
    """Render a ``<text>`` element; ``content`` is raw markup, escape untrusted strings."""
    return (
        f'<text x="{x:.0f}" y="{y:.0f}" fill="{fill}" '
        f'font-size="{size}" {MONO} {extra}>{content}</text>'
    )


def assemble_document(
    banner: BannerLayout,
    *,
    panel: str,
    legend: str,
    city: str,
    chrome: Chrome,
    underlay: str = "",
    overlay: str = "",
    border: bool = False,
) -> str:
    """Wrap the rendered layers in the SVG header, background and divider.

    HUD layers stay in raw canvas pixels (fixed size); only ``city`` is wrapped
    in the fit ``translate``/``scale``. ``underlay`` draws behind the city,
    ``overlay`` on top; ``chrome`` themes the background; ``border`` frames it.
    """
    width = banner.width
    height = banner.height

    header = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" {MONO}>'
    )
    background = (
        f"{_gradients(chrome)}<style>{font_face_css()}</style></defs>"
        f'<rect width="{width}" height="{height}" fill="url(#sky)"/>'
        f'<rect width="{width}" height="{height}" fill="url(#glow)"/>'
    )
    divider = (
        f'<line x1="{banner.divider_x:.0f}" y1="{banner.pad}" '
        f'x2="{banner.divider_x:.0f}" y2="{height - banner.pad}" '
        'stroke="#274038" stroke-width="1" stroke-opacity="0.5"/>'
    )
    content = (
        f'<g transform="translate({banner.content_tx:.2f},{banner.content_ty:.2f}) '
        f'scale({banner.scale:.4f})">{city}</g>'
    )
    # Inset by half the stroke width so the frame sits fully inside the viewBox.
    frame = (
        f'<rect x="0.75" y="0.75" width="{width - 1.5}" height="{height - 1.5}" '
        f'fill="none" stroke="{chrome.border_ink}" stroke-width="1.5"/>'
        if border
        else ""
    )

    return (
        header
        + background
        + underlay
        + content
        + panel
        + legend
        + overlay
        + divider
        + frame
        + "</svg>"
    )
