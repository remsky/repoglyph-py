"""The lit-window brightness mapping, shared by every city style."""

from __future__ import annotations

import math

__all__ = ["window_light"]

_UNLIT = "#0b1430"
#: Lit-window colour ramp endpoints, barely-touched -> hottest: a warm amber that
#: brightens toward white-cream so hue *and* opacity both track churn.
_LIT_COLD = (0xE8, 0xA8, 0x3C)
_LIT_HOT = (0xFF, 0xF4, 0xCC)


def _ramp(t: float) -> str:
    r, g, b = (round(_LIT_COLD[i] + (_LIT_HOT[i] - _LIT_COLD[i]) * t) for i in range(3))
    return f"#{r:02x}{g:02x}{b:02x}"


def window_light(touch: int, max_touch: int) -> tuple[str, float]:
    """Return the ``(fill, opacity)`` of a file's window for *touch* line churn."""
    if touch <= 0:
        return _UNLIT, 0.45
    tr = math.log1p(touch) / math.log1p(max_touch) if max_touch > 0 else 0.0
    return _ramp(tr), round(0.30 + tr * 0.65, 2)
