"""Named color themes: building face colors + page/HUD chrome, selectable and extensible."""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path

from repoglyph.palette import CATEGORY_COLORS, Category

__all__ = ["Palette", "Chrome", "DARK_CHROME", "PALETTES", "DEFAULT_PALETTE", "resolve_palette"]

type Triple = tuple[str, str, str]

#: Face order within a triple, lightest to darkest: (top, left, right).
_CATEGORIES: tuple[Category, ...] = ("code", "conf", "docs", "asset", "other")


@dataclass(frozen=True, slots=True)
class Chrome:
    """Page and HUD colors, representing everything that isn't a building face."""

    bg: Triple = ("#08150f", "#0d1f18", "#12261f")
    glow: str = "#25705a"
    glow_opacity: float = 0.5
    ink: str = "#eafbf4"  # title
    accent: str = "#5ef2d0"  # subtitle + logo stroke (the brand mark)
    stat: str = "#cfe4da"  # stat lines
    muted: str = "#93b8a8"  # notes + legend labels
    crowd_stroke: str = "#a2c4b4"  # stick-figure limbs
    box_stroke: str = "#bfe0d2"  # district floor outline
    #: Border around legend/note swatches (required for light themes).
    swatch_stroke: str = "none"
    #: District label text fill + halo color. ``None`` keeps each projection's own
    #: white-on-dark constants byte-for-byte; light themes set black-on-light.
    label_ink: str | None = None
    label_halo: str | None = None
    #: Optional thin outer frame stroke (drawn only when a border is requested).
    border_ink: str = "#ffffff"


@dataclass(frozen=True, slots=True)
class Palette:
    """A named theme: per-category ``(top, left, right)`` faces plus ``Chrome``."""

    name: str
    colors: dict[Category, Triple]
    chrome: Chrome = field(default_factory=Chrome)


#: Default dark chrome singleton (ruff B008).
DARK_CHROME = Chrome()

DEFAULT_PALETTE = "neon"

#: Built-in themes. ``neon`` is the canonical dark look (reuses ``CATEGORY_COLORS``
#: + default ``Chrome``); ``light`` is a light-background reskin.
PALETTES: dict[str, Palette] = {
    "neon": Palette("neon", dict(CATEGORY_COLORS)),
    "light": Palette(
        "light",
        {
            "code": ("#3dad94", "#1c6457", "#2c8674"),
            "conf": ("#d39e3a", "#8a601a", "#b1822a"),
            "docs": ("#6fb352", "#3c6628", "#52883a"),
            "asset": ("#9968c9", "#523080", "#7548a4"),
            "other": ("#7d8ea0", "#3c4854", "#5a6a78"),
        },
        Chrome(
            bg=("#d3dbec", "#c6d0e3", "#b9c4d9"),
            glow="#aebfe2",
            glow_opacity=0.45,
            ink="#080b14",
            accent="#06463b",
            stat="#080b14",
            muted="#2b3447",
            crowd_stroke="#333d50",
            box_stroke="#283142",
            swatch_stroke="#4a5468",
            label_ink="#0a0e18",
            label_halo="#eef2fb",
            border_ink="#000000",
        ),
    ),
}


def resolve_palette(spec: str | None) -> Palette:
    """Resolve a ``--palette`` value to a ``Palette``.

    ``None`` or a built-in name returns that palette; otherwise *spec* is a path
    to a palette JSON file. An unknown name that isn't a readable file raises
    ``ValueError``.
    """
    if spec is None:
        return PALETTES[DEFAULT_PALETTE]
    if spec in PALETTES:
        return PALETTES[spec]
    path = Path(spec)
    if path.is_file():
        return _load_file(path)
    raise ValueError(
        f"unknown palette {spec!r}; choose one of {', '.join(PALETTES)} or a palette JSON path"
    )


def _load_file(path: Path) -> Palette:
    """Load a custom palette JSON (missing keys fall back to defaults)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    colors: dict[Category, Triple] = dict(CATEGORY_COLORS)
    for category, triple in raw.get("colors", {}).items():
        if category not in _CATEGORIES:
            raise ValueError(f"palette {path}: unknown category {category!r} not in {_CATEGORIES}")
        strs = isinstance(triple, list) and all(isinstance(c, str) for c in triple)
        if not (strs and len(triple) == 3):
            raise ValueError(f"palette {path}: category {category!r} must be 3 hex color strings")
        colors[category] = (triple[0], triple[1], triple[2])
    return Palette(str(raw.get("name", path.stem)), colors, _load_chrome(raw.get("chrome", {})))


def _load_chrome(raw: dict) -> Chrome:
    """Build a ``Chrome`` from a JSON object, overriding only the keys present."""
    fields = {f.name for f in dataclasses.fields(Chrome)}
    overrides: dict = {}
    for key, value in raw.items():
        if key not in fields:
            raise ValueError(f"unknown chrome key {key!r}; expected {sorted(fields)}")
        overrides[key] = tuple(value) if key == "bg" else value
    return dataclasses.replace(Chrome(), **overrides)
