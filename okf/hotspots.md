---
type: "Report"
title: "Hotspots"
description: "Files ranked by line churn over the last 50 commits, plus change-coupling hubs."
tags: ["repoglyph", "churn"]
---

# Ranked by recent churn

| file | lines changed | size at HEAD | district |
| --- | --- | --- | --- |
| `AGENTS_NOTES.md` | 713 | 46.0 KB | .root |
| `src/repoglyph/okf.py` | 643 | 19.7 KB | src/repoglyph |
| `tests/parity/expected.json` | 601 | 9.5 KB | tests/parity |
| `src/repoglyph/cli.py` | 557 | 13.6 KB | src/repoglyph |
| `src/repoglyph/render/districts.py` | 478 | 16.1 KB | src/repoglyph/render |
| `README.md` | 419 | 4.7 KB | .root |
| `src/repoglyph/render/scene.py` | 392 | 13.2 KB | src/repoglyph/render |
| `src/repoglyph/render/highrise.py` | 391 | 14.0 KB | src/repoglyph/render |
| `src/repoglyph/render/overlay.py` | 317 | 9.0 KB | src/repoglyph/render |
| `tests/test_okf.py` | 254 | 8.3 KB | tests |
| `src/repoglyph/models.py` | 240 | 5.5 KB | src/repoglyph |
| `src/repoglyph/render/oblique.py` | 228 | 7.0 KB | src/repoglyph/render |
| `src/repoglyph/render/compose.py` | 217 | 7.6 KB | src/repoglyph/render |
| `src/repoglyph/geometry.py` | 210 | 6.2 KB | src/repoglyph |
| `src/repoglyph/gitsource.py` | 205 | 6.1 KB | src/repoglyph |
| `LICENSE` | 202 | 11.1 KB | .root |
| `tests/test_districts.py` | 173 | 5.0 KB | tests |
| `tests/test_render.py` | 156 | 3.3 KB | tests |
| `src/repoglyph/render/buildings.py` | 142 | 4.7 KB | src/repoglyph/render |
| `src/repoglyph/render/styles.py` | 136 | 4.7 KB | src/repoglyph/render |

(57 more touched files not shown.)

# Change-coupling hubs

Files that repeatedly change in the same commits, ranked by how many partners they co-change with (pairs sharing under 2 commits and bulk commits touching over 30 files are ignored). Broad coupling marks a structural hub; unexpected coupling marks a candidate for decoupling.

| file | coupled files | co-changes | strongest links |
| --- | --- | --- | --- |
| `README.md` | 23 | 70 | `src/repoglyph/cli.py` (8), `src/repoglyph/okf.py` (5), `.pre-commit-config.yaml` (4) |
| `src/repoglyph/cli.py` | 20 | 58 | `README.md` (8), `src/repoglyph/okf.py` (6), `tests/test_okf.py` (4) |
| `src/repoglyph/okf.py` | 14 | 40 | `src/repoglyph/cli.py` (6), `README.md` (5), `tests/test_okf.py` (4) |
| `assets/banner.png` | 12 | 31 | `README.md` (4), `.pre-commit-config.yaml` (3), `scripts/update_badges.py` (3) |
| `src/repoglyph/models.py` | 10 | 24 | `README.md` (3), `src/repoglyph/cli.py` (3), `src/repoglyph/okf.py` (3) |
| `tests/test_models.py` | 10 | 24 | `README.md` (3), `src/repoglyph/cli.py` (3), `src/repoglyph/models.py` (3) |
| `tests/test_okf.py` | 9 | 24 | `README.md` (4), `src/repoglyph/cli.py` (4), `src/repoglyph/okf.py` (4) |
| `.pre-commit-config.yaml` | 9 | 23 | `README.md` (4), `assets/banner.png` (3), `scripts/update_badges.py` (3) |
| `tests/test_render.py` | 9 | 20 | `README.md` (3), `src/repoglyph/cli.py` (3), `assets/banner.png` (2) |
| `scripts/update_badges.py` | 8 | 19 | `.pre-commit-config.yaml` (3), `README.md` (3), `assets/banner.png` (3) |
| `scripts/update_glyph.py` | 7 | 16 | `README.md` (3), `assets/banner.png` (3), `.pre-commit-config.yaml` (2) |
| `src/repoglyph/gitsource.py` | 6 | 12 | `README.md` (2), `src/repoglyph/cli.py` (2), `src/repoglyph/models.py` (2) |
| `tests/test_gitsource.py` | 6 | 12 | `README.md` (2), `src/repoglyph/cli.py` (2), `src/repoglyph/gitsource.py` (2) |
| `tests/test_metrics.py` | 6 | 12 | `README.md` (2), `src/repoglyph/cli.py` (2), `src/repoglyph/models.py` (2) |
| `CONTRIBUTING.md` | 5 | 10 | `README.md` (2), `assets/banner.png` (2), `scripts/update_glyph.py` (2) |

Context: [repository overview](repository.md).
