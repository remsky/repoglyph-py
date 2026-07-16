# AGENTS.md

Repoglyph generates isometric repo-city banners and OKF structural-context
bundles from a local git clone.

## Repo structural map (OKF bundle)

The machine-readable map of this codebase lives on the `glyph` orphan branch,
refreshed by CI on every push to `main`. It is intentionally kept off `main`:
it is derived data, and committing it per change churns the source history.

- Fetch: https://raw.githubusercontent.com/remsky/repoglyph-py/glyph/okf/index.md
- Locally after clone: `git show glyph:okf/index.md`
- Regenerate on demand: `repoglyph . --okf okf`

## Common commands

- Test: `uv run pytest`
- Lint: `uv run ruff check .`
- Render a banner locally: `repoglyph .`
