---
type: "Report"
title: "Hotspots"
description: "Files ranked by line churn over the last 50 commits, plus change-coupling hubs and oversized source files."
tags: ["repoglyph", "churn"]
---

# Ranked by recent churn

| file | lines changed | size at HEAD | district |
| --- | --- | --- | --- |
| `tests/parity/expected.json` | 601 | 9.5 KB | [tests/parity](districts/tests-parity.md) |
| `src/repoglyph/okf.py` | 550 | 17.7 KB | [src/repoglyph](districts/src-repoglyph.md) |
| `src/repoglyph/render/districts.py` | 478 | 16.1 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/cli.py` | 394 | 11.3 KB | [src/repoglyph](districts/src-repoglyph.md) |
| `src/repoglyph/render/scene.py` | 392 | 13.2 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/render/highrise.py` | 389 | 13.9 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/render/overlay.py` | 317 | 9.0 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `README.md` | 309 | 3.7 KB | [.root](districts/root.md) |
| `src/repoglyph/render/oblique.py` | 226 | 6.9 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/render/compose.py` | 215 | 7.5 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/geometry.py` | 210 | 6.2 KB | [src/repoglyph](districts/src-repoglyph.md) |
| `LICENSE` | 202 | 11.1 KB | [.root](districts/root.md) |
| `tests/test_okf.py` | 193 | 7.1 KB | [tests](districts/tests.md) |
| `src/repoglyph/gitsource.py` | 178 | 6.1 KB | [src/repoglyph](districts/src-repoglyph.md) |
| `tests/test_districts.py` | 173 | 5.0 KB | [tests](districts/tests.md) |
| `src/repoglyph/models.py` | 164 | 5.5 KB | [src/repoglyph](districts/src-repoglyph.md) |
| `tests/test_render.py` | 156 | 3.3 KB | [tests](districts/tests.md) |
| `src/repoglyph/render/buildings.py` | 142 | 4.7 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/render/styles.py` | 136 | 4.7 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/render/logo.py` | 132 | 5.0 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |

(51 more touched files not shown.)

# Change-coupling hubs

Files that repeatedly change in the same commits, ranked by how many partners they co-change with (pairs sharing under 2 commits and bulk commits touching over 30 files are ignored). Broad coupling marks a structural hub; unexpected coupling marks a candidate for decoupling.

| file | coupled files | co-changes | strongest links |
| --- | --- | --- | --- |
| `README.md` | 17 | 45 | `src/repoglyph/cli.py` (5), `assets/banner.png` (4), `.pre-commit-config.yaml` (3) |
| `src/repoglyph/cli.py` | 15 | 37 | `README.md` (5), `src/repoglyph/okf.py` (4), `assets/banner.png` (3) |
| `assets/banner.png` | 12 | 31 | `README.md` (4), `.pre-commit-config.yaml` (3), `scripts/update_badges.py` (3) |
| `src/repoglyph/okf.py` | 11 | 26 | `src/repoglyph/cli.py` (4), `README.md` (3), `assets/banner.png` (3) |
| `tests/test_render.py` | 9 | 20 | `README.md` (3), `src/repoglyph/cli.py` (3), `assets/banner.png` (2) |
| `.pre-commit-config.yaml` | 8 | 19 | `README.md` (3), `assets/banner.png` (3), `scripts/update_badges.py` (3) |
| `scripts/update_badges.py` | 8 | 19 | `.pre-commit-config.yaml` (3), `README.md` (3), `assets/banner.png` (3) |
| `scripts/update_glyph.py` | 7 | 16 | `README.md` (3), `assets/banner.png` (3), `.pre-commit-config.yaml` (2) |
| `src/repoglyph/models.py` | 6 | 12 | `README.md` (2), `assets/banner.png` (2), `src/repoglyph/cli.py` (2) |
| `tests/test_models.py` | 6 | 12 | `README.md` (2), `assets/banner.png` (2), `src/repoglyph/cli.py` (2) |
| `tests/test_okf.py` | 6 | 12 | `.pre-commit-config.yaml` (2), `README.md` (2), `assets/banner.png` (2) |
| `CONTRIBUTING.md` | 5 | 10 | `README.md` (2), `assets/banner.png` (2), `scripts/update_glyph.py` (2) |
| `pyproject.toml` | 4 | 8 | `.pre-commit-config.yaml` (2), `README.md` (2), `assets/banner.png` (2) |
| `src/repoglyph/render/districts.py` | 4 | 8 | `README.md` (2), `src/repoglyph/cli.py` (2), `tests/test_render.py` (2) |
| `tests/test_styles.py` | 4 | 8 | `README.md` (2), `src/repoglyph/cli.py` (2), `src/repoglyph/render/districts.py` (2) |

Context: [repository overview](repository.md).
