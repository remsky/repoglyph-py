"""Deterministic pseudo-random helpers for reproducible jitter (lighting, crowd)."""

from __future__ import annotations

import hashlib

__all__ = ["stable_unit"]


def stable_unit(*parts: object) -> float:
    """Return a deterministic float in ``[0, 1)`` derived from *parts*."""
    key = "_".join(map(str, parts)).encode()
    digest = int(hashlib.md5(key).hexdigest(), 16)
    return (digest % 10000) / 10000
