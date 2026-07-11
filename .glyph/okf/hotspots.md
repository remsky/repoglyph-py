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
| `src/repoglyph/okf.py` | 554 | 17.7 KB | [src/repoglyph](districts/src-repoglyph.md) |
| `src/repoglyph/render/districts.py` | 478 | 16.1 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/cli.py` | 403 | 11.3 KB | [src/repoglyph](districts/src-repoglyph.md) |
| `src/repoglyph/render/scene.py` | 392 | 13.2 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/render/highrise.py` | 389 | 13.9 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/render/overlay.py` | 317 | 9.0 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `README.md` | 313 | 3.8 KB | [.root](districts/root.md) |
| `src/repoglyph/models.py` | 240 | 5.5 KB | [src/repoglyph](districts/src-repoglyph.md) |
| `src/repoglyph/render/oblique.py` | 226 | 6.9 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/render/compose.py` | 215 | 7.5 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/geometry.py` | 210 | 6.2 KB | [src/repoglyph](districts/src-repoglyph.md) |
| `src/repoglyph/gitsource.py` | 205 | 6.1 KB | [src/repoglyph](districts/src-repoglyph.md) |
| `tests/test_okf.py` | 205 | 7.1 KB | [tests](districts/tests.md) |
| `LICENSE` | 202 | 11.1 KB | [.root](districts/root.md) |
| `tests/test_districts.py` | 173 | 5.0 KB | [tests](districts/tests.md) |
| `tests/test_render.py` | 156 | 3.3 KB | [tests](districts/tests.md) |
| `src/repoglyph/render/buildings.py` | 142 | 4.7 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/render/styles.py` | 136 | 4.7 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |
| `src/repoglyph/render/logo.py` | 132 | 5.0 KB | [src/repoglyph/render](districts/src-repoglyph-render.md) |

(52 more touched files not shown.)

# Change-coupling hubs

Files that repeatedly change in the same commits, ranked by how many partners they co-change with (pairs sharing under 2 commits and bulk commits touching over 30 files are ignored). Broad coupling marks a structural hub; unexpected coupling marks a candidate for decoupling.

| file | coupled files | co-changes | strongest links |
| --- | --- | --- | --- |
| `README.md` | 22 | 60 | `src/repoglyph/cli.py` (6), `assets/banner.png` (4), `src/repoglyph/okf.py` (4) |
| `src/repoglyph/cli.py` | 20 | 52 | `README.md` (6), `src/repoglyph/okf.py` (5), `assets/banner.png` (3) |
| `src/repoglyph/okf.py` | 14 | 37 | `src/repoglyph/cli.py` (5), `README.md` (4), `assets/banner.png` (3) |
| `assets/banner.png` | 12 | 31 | `README.md` (4), `.pre-commit-config.yaml` (3), `scripts/update_badges.py` (3) |
| `src/repoglyph/models.py` | 10 | 24 | `README.md` (3), `src/repoglyph/cli.py` (3), `src/repoglyph/okf.py` (3) |
| `tests/test_models.py` | 10 | 24 | `README.md` (3), `src/repoglyph/cli.py` (3), `src/repoglyph/models.py` (3) |
| `tests/test_okf.py` | 9 | 21 | `README.md` (3), `src/repoglyph/cli.py` (3), `src/repoglyph/okf.py` (3) |
| `tests/test_render.py` | 9 | 20 | `README.md` (3), `src/repoglyph/cli.py` (3), `assets/banner.png` (2) |
| `.pre-commit-config.yaml` | 8 | 19 | `README.md` (3), `assets/banner.png` (3), `scripts/update_badges.py` (3) |
| `scripts/update_badges.py` | 8 | 19 | `.pre-commit-config.yaml` (3), `README.md` (3), `assets/banner.png` (3) |
| `scripts/update_glyph.py` | 7 | 16 | `README.md` (3), `assets/banner.png` (3), `.pre-commit-config.yaml` (2) |
| `src/repoglyph/gitsource.py` | 6 | 12 | `README.md` (2), `src/repoglyph/cli.py` (2), `src/repoglyph/models.py` (2) |
| `tests/test_gitsource.py` | 6 | 12 | `README.md` (2), `src/repoglyph/cli.py` (2), `src/repoglyph/gitsource.py` (2) |
| `tests/test_metrics.py` | 6 | 12 | `README.md` (2), `src/repoglyph/cli.py` (2), `src/repoglyph/models.py` (2) |
| `CONTRIBUTING.md` | 5 | 10 | `README.md` (2), `assets/banner.png` (2), `scripts/update_glyph.py` (2) |

Context: [repository overview](repository.md).
