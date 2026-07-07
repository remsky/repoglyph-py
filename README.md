# repoglyph

Generate an isometric repo-city SVG from a local git clone.

Each file becomes a building. File size drives height, file type drives color,
and recent commits light windows. No network calls. No tokens.

## Install

From this checkout:

```bash
uv sync
uv run repoglyph path/to/repo
```

After PyPI release:

```bash
pip install repoglyph
repoglyph path/to/repo
```

Requires Python 3.12+.

## Usage

```bash
repoglyph                 # current repo
repoglyph ../project      # another local clone
repoglyph . --style skyline --palette neon
repoglyph . --commits 100 --out banner.svg
```

Default output:

```text
output/<owner>_<repo>/<owner>_<repo>_<style>.svg
```

If `resvg-py` is installed, a PNG is written beside the SVG. Use `--no-png` to
skip it.

## Main Options

| Flag | Default | Meaning |
| --- | --- | --- |
| `--commits N` | `50` | commits used for lit windows |
| `--style NAME` | `oblique` | `oblique`, `skyline`, or `highrise` |
| `--palette NAME\|FILE` | `light` | built-in theme or palette JSON |
| `--size WxH` | `1280x480` | SVG canvas size |
| `--full` | off | fit canvas to the whole city |
| `--out FILE` | auto | output SVG path |
| `--no-png` | off | skip PNG output |
| `--okf [DIR]` | off | write an OKF context bundle |

Run `repoglyph --help` for the full list.

## Styles

- `oblique`: flat cabinet-oblique map view.
- `skyline`: one building per file.
- `highrise`: one tower per district, with floors for subdirectories.

## OKF

`--okf` writes markdown context files from the same repo data:

```bash
repoglyph . --okf
repoglyph . --okf .knowledge
```

Output:

```text
okf/
  index.md
  repository.md
  hotspots.md
  districts/<name>.md
```

## Limits

- The image shows folder structure, not runtime architecture.
- Lit windows use the sampled commit window, not full history.
- File bytes are used as the size proxy.

## Development

```bash
uv run pytest
uv run ruff check src tests
uv run ruff format --check src tests
```

Project layout:

```text
src/repoglyph/
  cli.py
  gitsource.py
  cache.py
  models.py
  metrics/
  okf.py
  palette.py
  palettes.py
  render/
tests/
```

## License

Apache-2.0. Bundled Monaspace Xenon fonts are SIL OFL.
