"""Command-line interface for generating a repoglyph banner."""

from __future__ import annotations

import argparse
import dataclasses
import logging
import os
import sys
from pathlib import Path

from repoglyph import __version__
from repoglyph.cache import CACHE_DIR, load_city, repo_stem, save_city
from repoglyph.geometry import BANNER_HEIGHT, BANNER_WIDTH
from repoglyph.gitsource import CloneError, gather_city_from_path, git_available
from repoglyph.models import filter_files
from repoglyph.okf import write_okf_bundle
from repoglyph.palettes import PALETTES, resolve_palette
from repoglyph.render import (
    STYLES,
    StyleParams,
    render,
    typeface,
)

__all__ = ["build_parser", "main"]

logger = logging.getLogger(__name__)


def _parse_size(value: str) -> tuple[int, int]:
    """Parse a ``WxH`` size string into ``(width, height)``."""
    try:
        width_str, height_str = value.lower().split("x", 1)
        width, height = int(width_str), int(height_str)
    except ValueError as error:
        raise ValueError(f"invalid --size {value!r}; expected WxH, e.g. 1280x400") from error
    if width <= 0 or height <= 0:
        raise ValueError(f"invalid --size {value!r}; width and height must be positive")
    return width, height


def _write_png(svg_path: Path, *, scale: float) -> Path | None:
    """Rasterize *svg_path* to a sibling PNG, best-effort.

    Skips silently if resvg-py is not installed.
    """
    try:
        import resvg_py
    except ImportError:
        logger.info("png: resvg-py not installed; wrote SVG only (uv sync to enable PNG)")
        return None
    try:
        png = resvg_py.svg_to_bytes(
            svg_path=str(svg_path),
            zoom=scale,
            font_files=typeface.font_files(),
            font_family=typeface.FONT_FAMILY,
        )
    except Exception as error:  # noqa: BLE001 - PNG is a convenience; never abort on it
        logger.warning("png: rasterization failed (%s); wrote SVG only", error)
        return None
    out_path = svg_path.with_suffix(".png")
    out_path.write_bytes(png)
    return out_path


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the ``repoglyph`` command."""
    parser = argparse.ArgumentParser(
        prog="repoglyph",
        description="Generate an isometric repoglyph banner SVG from a local git repository.",
    )
    parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="path to a local git clone (default: the current directory); "
        "with --from-cache, the cached repo label",
    )
    parser.add_argument(
        "--commits",
        type=int,
        default=50,
        metavar="N",
        help="how many recent commits light the windows (default: 50)",
    )
    parser.add_argument(
        "--from-cache",
        action="store_true",
        help=f"skip fetching; load structural data from {CACHE_DIR}/ (populated by a prior run)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="do not write the structural data to the cache after fetching",
    )
    parser.add_argument(
        "--out",
        default=None,
        metavar="FILE",
        help="output .svg path (default: output/<owner>_<repo>/<owner>_<repo>_<style>.svg)",
    )
    parser.add_argument(
        "--size",
        default=f"{BANNER_WIDTH}x{BANNER_HEIGHT}",
        metavar="WxH",
        help=f"banner canvas size (default: {BANNER_WIDTH}x{BANNER_HEIGHT})",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="auto-size the canvas to the city instead of a fixed banner "
        "(no scaling; can be very large)",
    )
    parser.add_argument(
        "--style",
        choices=tuple(STYLES),
        default="oblique",
        help="city style: "
        + "; ".join(f"{name} ({spec.summary})" for name, spec in STYLES.items())
        + " (default: oblique)",
    )
    for knob in dataclasses.fields(StyleParams):
        default = knob.metadata.get("cli_default", knob.default)
        parser.add_argument(
            f"--{knob.name}",
            type=type(default),
            default=default,
            metavar="N",
            help=f"{knob.metadata['help']} (default: {default:g})",
        )
    parser.add_argument(
        "--text",
        type=float,
        default=1.0,
        metavar="N",
        help="HUD text size scale (default: 1.0)",
    )
    parser.add_argument(
        "--weight",
        choices=("churn", "files"),
        default="churn",
        help="how recent activity lights windows: churn (lines changed) or "
        "files (each touched file weighted equally) (default: churn)",
    )
    parser.add_argument(
        "--label-prefix",
        action="store_true",
        help="show the full district path on labels instead of the bare name",
    )
    parser.add_argument(
        "--no-labels",
        action="store_true",
        help="hide the district name labels (boxes/outlines, if any, still draw)",
    )
    parser.add_argument(
        "--border",
        action="store_true",
        help="draw a thin outer frame around the banner",
    )
    parser.add_argument(
        "--start-dir",
        default="",
        metavar="DIR",
        help="treat DIR as the repository root (re-root the tree)",
    )
    parser.add_argument(
        "--skip-dirs",
        default="",
        metavar="LIST",
        help="comma-separated directories to omit, e.g. tests,docs",
    )
    parser.add_argument(
        "--palette",
        default="light",
        metavar="NAME|FILE",
        help="color theme: a built-in (" + ", ".join(PALETTES) + ") or a path to a "
        "palette JSON (default: light)",
    )
    parser.add_argument(
        "--no-png",
        action="store_true",
        help="do not also write a PNG alongside the SVG",
    )
    parser.add_argument(
        "--png-scale",
        type=float,
        default=2.0,
        metavar="N",
        help="resolution multiplier for the PNG (default: 2.0)",
    )
    parser.add_argument(
        "--okf",
        nargs="?",
        const="",
        default=None,
        metavar="DIR",
        help="also write an Open Knowledge Format bundle (markdown concept files "
        "giving agents the repo's structural context) to DIR (default: okf/ beside the SVG)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)

    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.from_cache and not os.path.isdir(args.repo):
        parser.error(f"repo must be a path to a local git clone: {args.repo!r}")
    try:
        width, height = _parse_size(args.size)
    except ValueError as error:
        parser.error(str(error))
    try:
        palette = resolve_palette(args.palette)
    except (ValueError, OSError) as error:
        parser.error(str(error))

    try:
        if args.from_cache:
            data = load_city(args.repo)
        else:
            if not git_available():
                raise CloneError("git was not found on PATH")
            data = gather_city_from_path(args.repo, commit_window=args.commits)
            if not args.no_cache:
                save_city(data)
    except CloneError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(
            f"error: no cache for {args.repo}; run once without --from-cache first",
            file=sys.stderr,
        )
        return 1

    params = StyleParams(
        **{knob.name: getattr(args, knob.name) for knob in dataclasses.fields(StyleParams)}
    )
    skip_dirs = [d.strip() for d in args.skip_dirs.split(",") if d.strip()]
    try:
        svg = render(
            data,
            width=width,
            height=height,
            full=args.full,
            style=args.style,
            palette=palette,
            params=params,
            detail=args.detail,
            text_scale=args.text,
            weight=args.weight,
            label_prefix=args.label_prefix,
            show_labels=not args.no_labels,
            border=args.border,
            start_dir=args.start_dir,
            skip_dirs=skip_dirs,
        )
    except Exception as error:
        logger.debug("render failed", exc_info=True)
        print(f"error: style {args.style!r} failed to render: {error}", file=sys.stderr)
        return 1

    # data.repo is the resolved label (slug, or a local path's derived name).
    safe_repo = repo_stem(data.repo)
    out_path = (
        Path(args.out) if args.out else Path("output") / safe_repo / f"{safe_repo}_{args.style}.svg"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding="utf-8")

    png_path = None if args.no_png else _write_png(out_path, scale=args.png_scale)

    okf_note = ""
    if args.okf is not None:
        okf_dir = Path(args.okf) if args.okf else out_path.parent / "okf"
        files, touches = filter_files(
            data.files, data.touches, start_dir=args.start_dir, skip_dirs=skip_dirs
        )
        okf_data = dataclasses.replace(data, files=files, touches=touches)
        doc_count = write_okf_bundle(okf_data, okf_dir)
        okf_note = f" + {okf_dir}{os.sep} ({doc_count} docs)"

    wrote = str(out_path) + (f" + {png_path.name}" if png_path else "") + okf_note
    print(f"wrote {wrote}  ({len(data.files)} buildings, {len(data.touches)} lit)")
    return 0
