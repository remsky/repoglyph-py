"""Refresh the committed banner, OKF bundle, and plugin skill, staging the result.

Self-staging keeps the commit green on the first try; a nonzero exit means a
real error, not "run me again".
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PNG = ROOT / ".glyph" / "repoglyph-py_oblique.png"
BANNER = ROOT / "assets" / "banner.png"
OKF = ROOT / ".glyph" / "okf"
README = ROOT / "README.md"
SKILL = ROOT / "plugin" / "skills" / "repoglyph" / "SKILL.md"

SKILL_FRONTMATTER = """\
---
name: repoglyph
description: Generate isometric repo-city banners and OKF structural context bundles from a local git clone with the repoglyph CLI. Use when the user wants a repo banner image, a codebase map, an agent-readable repo summary, or a self-updating repo-map skill.
---

"""

GENERATE = [
    *("uv", "run", "repoglyph", "."),
    *("--palette", "neon", "--border", "--detail", "28"),
    "--skip-commons",
    "--staged",
    "--okf",
]

#: Staging the refreshed banner changes the tree it depicts; fixed point by pass 3.
MAX_PASSES = 4


def _bundle() -> dict[str, bytes]:
    return {str(p.relative_to(OKF)): p.read_bytes() for p in sorted(OKF.rglob("*.md"))}


def _skill_from_readme() -> str:
    lines = README.read_text(encoding="utf-8").splitlines()
    body = "\n".join(line for line in lines if not line.lstrip().startswith(("![", "[![")))
    return SKILL_FRONTMATTER + re.sub(r"\n{3,}", "\n\n", body).strip() + "\n"


def _refresh() -> list[str]:
    """One generate pass; returns the repo-relative paths it changed."""
    before = _bundle() if OKF.exists() else {}
    result = subprocess.run(GENERATE, capture_output=True, text=True, cwd=ROOT)
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit(result.returncode)
    changed = []
    if not BANNER.exists() or BANNER.read_bytes() != PNG.read_bytes():
        shutil.copyfile(PNG, BANNER)
        changed.append("assets/banner.png")
    skill = _skill_from_readme()
    if not SKILL.exists() or SKILL.read_text(encoding="utf-8") != skill:
        SKILL.write_text(skill, encoding="utf-8")
        changed.append("plugin/skills/repoglyph/SKILL.md")
    if _bundle() != before:
        changed.append(".glyph/okf")
    return changed


def main() -> int:
    staged: set[str] = set()
    for _ in range(MAX_PASSES):
        changed = _refresh()
        if not changed:
            break
        staged.update(changed)
        subprocess.run(["git", "add", "-A", *changed], check=True, cwd=ROOT)
    else:
        print(f"error: outputs still changing after {MAX_PASSES} passes; not converging")
        return 1
    if staged:
        print("refreshed and staged into this commit: " + ", ".join(sorted(staged)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
