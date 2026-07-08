"""Refresh the README tests/coverage badges from a live pytest run, staging the result."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"


def main() -> int:
    result = subprocess.run(
        ["uv", "run", "pytest", "--cov=repoglyph", "tests"],
        capture_output=True,
        text=True,
        cwd=README.parent,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
        return result.returncode
    passed = re.search(r"(\d+) passed", result.stdout)
    total = re.search(r"TOTAL\s.*?(\d+)%", result.stdout)
    if not passed or not total:
        sys.stderr.write("could not parse pytest output:\n" + result.stdout)
        return 1
    text = README.read_text(encoding="utf-8")
    updated = re.sub(r"badge/tests-\d+-", f"badge/tests-{passed.group(1)}-", text)
    updated = re.sub(r"badge/coverage-\d+%25-", f"badge/coverage-{total.group(1)}%25-", updated)
    if updated != text:
        README.write_text(updated, encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], check=True, cwd=README.parent)
        print(
            f"README badges refreshed and staged into this commit "
            f"(tests {passed.group(1)}, coverage {total.group(1)}%)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
