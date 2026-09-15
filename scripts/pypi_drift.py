#!/usr/bin/env python3
# Imports pypi_members, which owns the index lookup and needs `packaging` for the PEP 440
# comparison — so this script declares the same PEP 723 dependency and runs the same way,
# `uv run --script`. The job that calls it never `uv sync`s.
# /// script
# requires-python = ">=3.11"
# dependencies = ["packaging>=25"]
# ///
"""Fail a change set that moves a published PyPI-lane member without bumping its version.

The platform lane embeds internal libraries from source at the release commit.
So a lane member can change, merge, and run in production while PyPI keeps serving that
same version number with the old content. This is the check that prevents it.

The rule: a member whose shipped content changed must declare a version the index does
not already serve.

A README is the project page on PyPI, where every version keeps it for good, so its
links to this repository must still resolve. The same run checks them for every changed
member, which catches a stale link in the bump that ships it, not after the file moved.

A bump does not claim the change was significant — semver's major/minor/patch carries
that, and the author still chooses it. It asserts only that this content is not the content
already published. Nothing is released on merge either: publishing still needs a pushed
tag, so bumps accumulate and one run ships them together.

Usage (`uv run --script`, so the PEP 723 block above resolves):
    git diff --name-only origin/main...HEAD | uv run --script scripts/pypi_drift.py
    git diff --name-only origin/main...HEAD | uv run --script scripts/pypi_drift.py --list
    git diff --name-only origin/main...HEAD \
        | uv run --script scripts/pypi_drift.py --base "$(git merge-base origin/main HEAD)"
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

import tomllib

from pypi_members import IndexedMember, pypi_members, release_candidates

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Root files that reach consumers alongside the code: pyproject.toml becomes the wheel's
# METADATA, the README its Description on the project page, the LICENSE ships in
# .dist-info. Prefix-matched, so README.md and LICENSE.txt are both picked up.
METADATA_FILES = ("pyproject.toml", "README", "LICENSE")

# Absolute links are the only kind that work on the PyPI project page.
REPO_LINK = re.compile(
    r"https://github\.com/ghga-de/ghga/(?:blob|tree)/main/([^)\s#?\"'<>]+)"
)

# First line of a file left behind at an old path, so that links already published on
# PyPI keep resolving. A stub is a target for those, never for a new release.
MOVED_MARKER = "<!-- moved:"


def _packaged_roots(member_path: str) -> list[str]:
    """Reads the directories a member's distribution is built from, e.g. `["src"]`.

    Taken from the member's own `[tool.setuptools.packages.find] where`, so "shipped"
    here means the same thing it means to the build backend, rather than a second guess
    that could drift from it.

    Args:
        member_path: The member's folder relative to the repo root, e.g. `libs/hexkit`.

    Returns:
        The packaged root directories, empty when they cannot be established — a build
        backend other than setuptools, or the table missing.
    """
    manifest = tomllib.loads((ROOT / member_path / "pyproject.toml").read_text())
    return list(
        manifest.get("tool", {})
        .get("setuptools", {})
        .get("packages", {})
        .get("find", {})
        .get("where", [])
    )


def _same_toml(base: str, file: str) -> bool:
    """Tells whether a TOML file parses to the same data at `base` as in the working tree.

    Comments and formatting in `pyproject.toml` never reach the wheel's METADATA, so a
    change to only those ships nothing.

    Args:
        base: The commit the change set is compared against.
        file: The file path, relative to the repo root.

    Returns:
        True only if both versions exist, parse, and are equal; anything that cannot be
        compared counts as changed.
    """
    try:
        before = subprocess.run(
            ["git", "show", f"{base}:{file}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return tomllib.loads(before) == tomllib.loads((ROOT / file).read_text())
    except (subprocess.CalledProcessError, OSError, tomllib.TOMLDecodeError):
        return False


def changed_members(files: list[str], base: str | None = None) -> list[str]:
    """Selects the lane members whose shipped content `files` touches.

    Deliberately not `affected_targets.affected()`, which answers "what might this break?"
    and is right to over-approximate: it expands to dependents — whose own distributions
    do not change when a dependency does — and treats repo-wide paths such as `scripts/`
    or `.github/workflows/` as touching every member, none of which ship inside a wheel.
    Reusing it here would demand a version bump of every lane member for a workflow edit.

    Args:
        files: Changed file paths, relative to the repo root.
        base: The commit `files` were diffed against. When given, a `pyproject.toml`
            whose parsed content is unchanged, such as a comment-only edit, is ignored.

    Returns:
        The sorted member folders whose shipped content changed, e.g. `["libs/hexkit"]`.

    Raises:
        SystemExit: if any lane member's packaged roots cannot be established. Treating
            one as "ships nothing" would let it drift forever while this check stayed
            green — the failure the check exists to prevent.
    """
    roots = {member.path: _packaged_roots(member.path) for member in pypi_members()}
    unknown = sorted(path for path, found in roots.items() if not found)
    if unknown:
        sys.exit(
            "error: cannot establish what these members ship, so drift in them would go"
            f" unnoticed: {', '.join(unknown)}"
        )

    if base is not None:
        files = [
            f
            for f in files
            if not (f.endswith("/pyproject.toml") and _same_toml(base, f))
        ]

    changed = set()
    for path, packaged in roots.items():
        shipped = tuple(f"{pathlib.PurePosixPath(path, root)}/" for root in packaged)
        metadata = tuple(f"{path}/{name}" for name in METADATA_FILES)
        if any(f.startswith(metadata) or f.startswith(shipped) for f in files):
            changed.add(path)
    return sorted(changed)


def readme_link_problems(member_path: str) -> list[str]:
    """Finds links in a member's README that do not lead to a current file in this repo.

    Args:
        member_path: The member's folder relative to the repo root, e.g. `libs/hexkit`.

    Returns:
        One message per link that points to a missing path or to a moved-file stub.
    """
    problems = []
    for readme in sorted((ROOT / member_path).glob("README*")):
        for target in REPO_LINK.findall(readme.read_text()):
            path = ROOT / target.rstrip("/")
            name = readme.relative_to(ROOT)
            if not path.exists():
                problems.append(f"{name}: link to {target}, which does not exist")
            elif path.is_file() and path.read_text().startswith(MOVED_MARKER):
                problems.append(f"{name}: link to {target}, which has moved")
    return problems


def unbumped_members(member_paths: set[str]) -> list[IndexedMember]:
    """Finds which of `member_paths` still declare a version the index already serves.

    Args:
        member_paths: The member folders whose shipped content changed.

    Returns:
        The members among them that need a version bump, each carrying the `reason`
        `release_candidates` passed it over for.

    Raises:
        SystemExit: if PyPI cannot be reached for one of them, since nothing can be
            asserted against an unknown index.
    """
    # Narrowed before the lookup, not after: the index is asked only about the members
    # the change set touched, so an outage on an unrelated lane member cannot fail a run
    # that had nothing to do with it.
    changed = [member for member in pypi_members() if member.path in member_paths]
    candidates = release_candidates(changed)
    if candidates.unreachable:
        unreachable = ", ".join(member.package for member in candidates.unreachable)
        sys.exit(
            "error: could not reach PyPI to establish what is already released:"
            f" {unreachable}"
        )
    return candidates.skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list",
        action="store_true",
        help="print the lane members the change set ships into and stop, without asking"
        " the index anything",
    )
    parser.add_argument(
        "--base",
        help="the commit the file list was diffed against; lets a comment-only"
        " pyproject.toml change pass",
    )
    args = parser.parse_args(argv)

    changed = changed_members(sys.stdin.read().splitlines(), args.base)
    if args.list:
        print("\n".join(changed))
        return 0
    if not changed:
        print("no PyPI-lane member's shipped content changed")
        return 0

    print("changed lane members: " + ", ".join(changed))
    link_problems = [p for member in changed for p in readme_link_problems(member)]
    for problem in link_problems:
        print(f"{problem} — point it at a current file", file=sys.stderr)
    needing_a_bump = unbumped_members(set(changed))
    for member in needing_a_bump:
        print(
            f"{member.package}: {member.reason}, but its shipped content changed"
            " — bump it, or the platform and PyPI disagree about what that version"
            " contains",
            file=sys.stderr,
        )
    return 1 if needing_a_bump or link_problems else 0


if __name__ == "__main__":
    sys.exit(main())
