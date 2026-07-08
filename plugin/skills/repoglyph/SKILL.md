---
name: repoglyph
description: Generate isometric repo-city banners and OKF structural context bundles from a local git clone with the repoglyph CLI. Use when the user wants a repo banner image, a codebase map, an agent-readable repo summary, or a self-updating repo-map skill.
---

# repoglyph

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
