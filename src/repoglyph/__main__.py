"""Allow ``python -m repoglyph`` to invoke the command-line interface."""

from __future__ import annotations

from repoglyph.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
