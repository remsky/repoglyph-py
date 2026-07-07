"""Map a file path to a category and a (top, left, right) color triple by extension."""

from __future__ import annotations

import os
from typing import Literal

__all__ = ["Category", "CATEGORY_COLORS", "CATEGORIES", "categorize"]

type Category = Literal["code", "conf", "docs", "asset", "other"]

#: Extensions grouped by category. Anything unmatched falls through to "other".
_EXTENSIONS: dict[Category, frozenset[str]] = {
    "code": frozenset(
        {
            ".py",
            ".js",
            ".mjs",
            ".ts",
            ".tsx",
            ".jsx",
            ".go",
            ".rs",
            ".c",
            ".cpp",
            ".cc",
            ".h",
            ".hpp",
            ".java",
            ".rb",
            ".sh",
            ".vue",
            ".svelte",
            ".kt",
            ".scala",
            ".swift",
            ".r",
            ".jl",
            ".lua",
            ".pyx",
        }
    ),
    "conf": frozenset(
        {
            ".json",
            ".yml",
            ".yaml",
            ".toml",
            ".ini",
            ".cfg",
            ".lock",
            ".env",
            ".xml",
            ".cmake",
        }
    ),
    "docs": frozenset({".md", ".txt", ".rst", ".mdx", ".ipynb"}),
    "asset": frozenset(
        {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".mp3",
            ".wav",
            ".pt",
            ".bin",
            ".onnx",
            ".webp",
            ".ico",
            ".ttf",
            ".woff",
            ".woff2",
            ".parquet",
            ".csv",
            ".arrow",
        }
    ),
}

#: (top, left, right) face colors for each category.
CATEGORY_COLORS: dict[Category, tuple[str, str, str]] = {
    "code": ("#3fae93", "#15564a", "#247d6b"),
    "conf": ("#c9a23f", "#7a5210", "#a87c1f"),
    "docs": ("#74ab4f", "#314f1c", "#4f7d30"),
    "asset": ("#9a5fc7", "#46236a", "#6e3a9e"),
    "other": ("#7d90a3", "#2f3a47", "#4d5d6d"),
}

#: Categories in legend display order, paired with their human-readable label.
CATEGORIES: tuple[tuple[Category, str], ...] = (
    ("code", "code"),
    ("conf", "config"),
    ("docs", "docs"),
    ("asset", "assets"),
    ("other", "other"),
)


def categorize(path: str) -> Category:
    """Classify *path* into a ``Category`` by its file extension."""
    extension = os.path.splitext(path)[1].lower()
    for category, extensions in _EXTENSIONS.items():
        if extension in extensions:
            return category
    return "other"
