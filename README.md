# <img src="https://raw.githubusercontent.com/remsky/repoglyph-py/main/assets/logo.svg" width="28" height="28" alt=""> repoglyph

[![OKF](https://img.shields.io/badge/bundle-OKF-0d1c17?labelColor=4c566a&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI%2BPGcgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNWVmMmQwIiBzdHJva2Utd2lkdGg9IjIuMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cGF0aCBkPSJNNiAyaDhsNCA0djE2SDZ6Ii8%2BPHBhdGggZD0iTTE0IDJ2NGg0Ii8%2BPHBhdGggZD0iTTkgOWgyLjVNMTMuNSA5SDE2Ii8%2BPHBhdGggZD0iTTkgMTMuNWg3TTkgMTcuNWg0LjUiLz48L2c%2BPC9zdmc%2BCg%3D%3D)](https://github.com/remsky/repoglyph-py/blob/main/.glyph/okf/index.md)

![tests](https://img.shields.io/badge/tests-88-5ef2d0)
![coverage](https://img.shields.io/badge/coverage-86%25-5ef2d0)

![repoglyph banner](https://raw.githubusercontent.com/remsky/repoglyph-py/main/assets/banner.png)

Isometric repo-city banners from a local git clone. Each file is a building:
size drives height, type drives color, recent commits light windows.

Offline port of [repoglyph.net](https://repoglyph.net); hosted (free)
customization explorer and web-cached banners there.

## Install

```bash
uv tool install "repoglyph[png]"   # standalone CLI on PATH
pip install "repoglyph[png]"       # CLI in the active environment
uv add --dev "repoglyph[png]"      # project dev dependency (CI, hooks)
```

Each installs the `repoglyph` command. Python 3.12+. Drop the `png` extra for
SVG-only output.

## Usage

```bash
repoglyph                 # current repo w/ defaults
repoglyph ../project
repoglyph . --style skyline --palette neon
```

Writes `<repo>/.glyph/<owner>_<repo>_<style>.svg`, plus a PNG with the `png` extra.

<details>
<summary><b>All flags</b></summary>

| Flag | Default | Meaning |
| --- | --- | --- |
| `--commits N` | `50` | commits used for lit windows |
| `--style NAME` | `oblique` | `oblique`, `skyline`, or `highrise` |
| `--palette NAME\|FILE` | `light` | built-in theme or palette JSON |
| `--size WxH` | `1280x480` | canvas size |
| `--full` | off | fit canvas to the whole city |
| `--out FILE` | auto | output SVG path |
| `--out-dir DIR` | `<repo>/.glyph` | folder for all outputs |
| `--no-png` | off | skip PNG output |
| `--skip-commons` | off | drop lockfiles from the city |
| `--staged` | off | draw HEAD + staged changes |
| `--okf [DIR]` | off | write an OKF context bundle |
| `--skill` | off | add a SKILL.md to the OKF bundle |
| `--cache` | off | save repo data for `--from-cache` |

`repoglyph --help` for the rest.

</details>

<details>
<summary><b>Styles</b></summary>

- `oblique`: flat cabinet-oblique map (default)
- `skyline`: one building per file
- `highrise`: one tower per district, floors are subdirs

</details>

## OKF

`--okf` writes markdown context files from the same repo data: an index,
repository and hotspot summaries, and one file per district.

Add `--skill` and point it at a skills folder to ship the bundle as a
self-updating map-of-the-codebase agent skill:

```bash
repoglyph . --okf .claude/skills/repo-map --skill
```

That one command is the whole install: Claude Code discovers anything under
`.claude/skills/` automatically. Commit the folder and every clone has it.

This repo is also a Claude Code plugin marketplace for itself; the plugin
ships a usage skill so Claude knows how to run repoglyph:

```bash
claude plugin marketplace add remsky/repoglyph-py
claude plugin install repoglyph@repoglyph
```

<details>
<summary><b>Limits</b></summary>

- Shows folder structure, not runtime architecture.
- Lit windows use the sampled commit window, not full history.
- File bytes proxy size.

</details>

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache-2.0. Bundled Monaspace Xenon fonts are SIL OFL.
