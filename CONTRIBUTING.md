# Contributing

repoglyph is managed with [uv](https://docs.astral.sh/uv/). Python 3.12+.

## Setup

```bash
uv sync
uv run pytest
uv run ruff check src tests
```

## Pre-commit hooks

```bash
prek install
```

Two local hooks keep the committed artifacts in sync with the code:

- `readme-badges` reruns the suite with coverage and rewrites the README shields.
- `repoglyph-outputs` regenerates `assets/banner.png` and the `.glyph/okf` bundle
  from the staged tree (`--staged --skip-commons`), so each commit ships a
  banner and bundle describing its own tree. It also rebuilds the plugin usage
  skill (`plugin/skills/repoglyph/SKILL.md`) from the README, so never edit
  that file directly.

Both hooks stage what they refresh, so the commit succeeds on the first try;
the hook output lists anything that was pulled in. The banner regenerates in
up to three passes because its own bytes feed back into the city it draws.

## Tests

Golden tests compare rendered SVGs byte for byte against `tests/goldens`. If a
render change is intentional, run the suite once with
`REPOGLYPH_REGEN_GOLDENS=1` and review the diff.
