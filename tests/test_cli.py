from __future__ import annotations

from pathlib import Path

from repoglyph.cli import DEFAULT_SKILL_DIR, resolve_image_outputs, resolve_okf_target


def test_no_flags_writes_nothing() -> None:
    assert resolve_okf_target(skill=None, okf=None, repo=".", out_dir=Path(".glyph")) is None


def test_okf_bare_defaults_beside_svg() -> None:
    target = resolve_okf_target(skill=None, okf="", repo=".", out_dir=Path(".glyph"))
    assert target == (Path(".glyph/okf"), False)


def test_okf_custom_path() -> None:
    target = resolve_okf_target(skill=None, okf="out/bundle", repo=".", out_dir=Path(".glyph"))
    assert target == (Path("out/bundle"), False)


def test_skill_bare_defaults_under_repo() -> None:
    target = resolve_okf_target(skill="", okf=None, repo="proj", out_dir=Path(".glyph"))
    assert target == (Path("proj") / DEFAULT_SKILL_DIR, True)


def test_skill_custom_path() -> None:
    target = resolve_okf_target(skill=".claude/skills/map", okf=None, repo=".", out_dir=Path("."))
    assert target == (Path(".claude/skills/map"), True)


def test_skill_wins_over_okf_and_stays_backcompat() -> None:
    # Legacy `--okf DIR --skill` still lands the bundle at DIR in skill mode.
    target = resolve_okf_target(skill="", okf="legacy/dir", repo=".", out_dir=Path("."))
    assert target == (Path("legacy/dir"), True)


def test_banner_mode_writes_both_images_by_default() -> None:
    assert resolve_image_outputs(svg=None, png=None, bundle_mode=False) == (True, True)


def test_bundle_mode_writes_no_image_by_default() -> None:
    assert resolve_image_outputs(svg=None, png=None, bundle_mode=True) == (False, False)


def test_explicit_flags_override_in_bundle_mode() -> None:
    assert resolve_image_outputs(svg=True, png=None, bundle_mode=True) == (True, False)
    assert resolve_image_outputs(svg=None, png=True, bundle_mode=True) == (False, True)


def test_no_png_still_opts_out_in_banner_mode() -> None:
    assert resolve_image_outputs(svg=None, png=False, bundle_mode=False) == (True, False)
