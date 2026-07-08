"""Refresh the committed banner and OKF bundle from a live repoglyph run."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PNG = ROOT / ".glyph" / "repoglyph-py_oblique.png"
BANNER = ROOT / "assets" / "banner.png"
OKF = ROOT / ".glyph" / "okf"

GENERATE = [
    *("uv", "run", "repoglyph", "."),
    *("--palette", "neon", "--border", "--detail", "28"),
    "--skip-commons",
    "--staged",
    "--okf",
]


def _bundle() -> dict[str, bytes]:
    return {str(p.relative_to(OKF)): p.read_bytes() for p in sorted(OKF.rglob("*.md"))}


def main() -> int:
    before = _bundle() if OKF.exists() else {}
    result = subprocess.run(GENERATE, capture_output=True, text=True, cwd=ROOT)
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        return result.returncode
    stale_banner = not BANNER.exists() or BANNER.read_bytes() != PNG.read_bytes()
    if stale_banner:
        shutil.copyfile(PNG, BANNER)
    if stale_banner or _bundle() != before:
        print("banner/OKF refreshed; re-stage assets/banner.png and .glyph/okf")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
