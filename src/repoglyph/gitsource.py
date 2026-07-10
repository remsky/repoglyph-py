"""Gather CityData from a local git clone (no network)."""

from __future__ import annotations

import logging
import os
import re
import subprocess
from collections import Counter

from repoglyph.models import CityData, SourceFile

__all__ = ["CloneError", "git_available", "gather_city_from_path"]

logger = logging.getLogger(__name__)

_OWNER_SEG = r"(?!\.\.?/)[A-Za-z0-9._-]+"
_REPO_SEG = r"(?!\.\.?(?:\.git)?/?$)[A-Za-z0-9._-]+?"
#: ``owner/repo`` out of an https or ssh github.com remote URL.
_REMOTE_RE = re.compile(
    rf"github\.com[:/](?P<slug>{_OWNER_SEG}/{_REPO_SEG})(?:\.git)?/?$",
    re.IGNORECASE,
)


class CloneError(RuntimeError):
    """Raised when reading the repository via git fails."""


def git_available() -> bool:
    """Return whether a usable ``git`` executable is on ``PATH``."""
    try:
        subprocess.run(
            ["git", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def gather_city_from_path(
    path: str,
    *,
    commit_window: int = 50,
    staged: bool = False,
) -> CityData:
    """Assemble ``CityData`` from an existing local clone at *path* (no network fetch).

    The label is the ``owner/repo`` slug derived from the ``origin`` remote when
    it points at github.com, otherwise the directory name. With *staged* the tree
    is read from the index (HEAD + staged changes) and the sha gets a ``+staged``
    marker; the churn window stays the last commits at HEAD.
    """
    repo_dir = os.path.abspath(path)
    try:
        _git(repo_dir, "rev-parse", "--is-inside-work-tree")
        slug = _slug_from_remote(repo_dir)
        label = slug or os.path.basename(repo_dir.rstrip("\\/")) or repo_dir
        logger.info("[1/2] reading local clone %s ...", repo_dir)
        return _gather_from_dir(repo_dir, label=label, commit_window=commit_window, staged=staged)
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or "").strip() or f"git exited {error.returncode}"
        raise CloneError(detail) from error
    except OSError as error:
        raise CloneError(str(error)) from error


def _gather_from_dir(repo_dir: str, *, label: str, commit_window: int, staged: bool) -> CityData:
    logger.info("[2/2] reading tree + last %d commits ...", commit_window)
    head_sha = _git(repo_dir, "rev-parse", "HEAD").strip()
    tree = "HEAD"
    if staged:
        # write-tree snapshots the index as a tree object without moving any ref.
        tree = _git(repo_dir, "write-tree").strip()
        head_sha += "+staged"
    files = _parse_ls_tree(_git(repo_dir, "ls-tree", "-r", "--long", tree))
    touches, commit_files = _parse_log(
        _git(
            repo_dir,
            "log",
            f"-n{commit_window}",
            "--numstat",
            "--no-renames",
            "--format=%H",
        )
    )

    return CityData(
        repo=label,
        files=files,
        touches=touches,
        commit_files=commit_files,
        commit_window=commit_window,
        head_sha=head_sha,
    )


# --------------------------------------------------------------------------
# git invocation
# --------------------------------------------------------------------------
def _git(repo_dir: str, *args: str) -> str:
    """Run a git command in *repo_dir* and return its stdout.

    ``core.quotepath=false`` keeps non-ASCII paths verbatim instead of
    octal-escaped.
    """
    result = subprocess.run(
        ["git", "-C", repo_dir, "-c", "core.quotepath=false", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def _slug_from_remote(repo_dir: str) -> str | None:
    """``owner/repo`` from the ``origin`` remote when it points at github.com."""
    try:
        url = _git(repo_dir, "remote", "get-url", "origin").strip()
    except subprocess.CalledProcessError:
        return None
    match = _REMOTE_RE.search(url)
    return match.group("slug") if match else None


# --------------------------------------------------------------------------
# pure parsing (unit-tested without git)
# --------------------------------------------------------------------------
def _parse_ls_tree(output: str) -> list[SourceFile]:
    """Parse ``git ls-tree -r --long HEAD`` into source files.

    Each line is ``<mode> <type> <sha> <size>\\t<path>``; only blobs are kept
    (submodules report type ``commit`` and a ``-`` size).
    """
    files: list[SourceFile] = []
    for line in output.splitlines():
        meta, _, path = line.partition("\t")
        if not path:
            continue
        fields = meta.split()
        if len(fields) < 4 or fields[1] != "blob":
            continue
        size = int(fields[3]) if fields[3].isdigit() else 0
        files.append(SourceFile(path=path, size=size))
    return files


#: A ``--format=%H`` commit-header line (sha1 or sha256 repos).
_SHA_LINE_RE = re.compile(r"^[0-9a-f]{40,64}$")


def _parse_log(output: str) -> tuple[dict[str, int], list[list[str]]]:
    """Parse ``git log --numstat --format=%H`` into churn totals and per-commit paths.

    Per file, churn is summed additions + deletions across the listed commits;
    binary files report ``-`` for both and count as ``1`` (touched, no line
    count). Commits with no file changes (e.g. merges) are dropped.
    """
    touches: Counter[str] = Counter()
    commits: list[list[str]] = []
    current: list[str] | None = None
    for line in output.splitlines():
        if _SHA_LINE_RE.match(line):
            current = []
            commits.append(current)
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        path = path.strip()
        if not path:
            continue
        try:
            touches[path] += int(added) + int(deleted)
        except ValueError:
            touches[path] += 1  # binary ("-\t-"): mark touched, no line count
        if current is not None:
            current.append(path)
    return dict(touches), [c for c in commits if c]
