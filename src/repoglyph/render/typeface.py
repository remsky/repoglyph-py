"""The bundled Monaspace Xenon typeface: ``@font-face`` CSS and sfnt paths."""

from __future__ import annotations

import base64
import functools
from pathlib import Path

__all__ = ["FONT_FAMILY", "font_face_css", "font_files"]

#: The family name every ``font-family`` stack leads with (see ``svg.MONO``).
FONT_FAMILY = "Monaspace Xenon"

_FONTS = Path(__file__).parent / "fonts"
#: (woff2 file, weight) for the embedded faces: Regular for body, Bold (700) for title.
_WOFF2_FACES = (
    ("MonaspaceXenon-Regular.subset.woff2", 400),
    ("MonaspaceXenon-Bold.subset.woff2", 700),
)
#: The sfnt faces handed to resvg's fontdb.
_OTF_FACES = (
    "MonaspaceXenon-Regular.subset.otf",
    "MonaspaceXenon-Bold.subset.otf",
)


@functools.cache
def font_face_css() -> str:
    """The ``@font-face`` rules with each face base64-embedded as a data URI.

    Cached (font bytes are fixed); goes in the SVG ``<defs><style>`` to stay self-contained.
    """
    rules: list[str] = []
    for name, weight in _WOFF2_FACES:
        data = base64.b64encode((_FONTS / name).read_bytes()).decode("ascii")
        rules.append(
            f'@font-face{{font-family:"{FONT_FAMILY}";'
            f"font-weight:{weight};font-style:normal;"
            f'src:url("data:font/woff2;base64,{data}") format("woff2");}}'
        )
    return "".join(rules)


def font_files() -> list[str]:
    """Filesystem paths to the sfnt faces, for resvg's ``font_files``."""
    return [str(_FONTS / name) for name in _OTF_FACES]
