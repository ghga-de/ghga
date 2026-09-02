#!/usr/bin/env python3
# Imports pypi_members, which owns the index lookup and needs `packaging` for the PEP 440
# comparison — so this script declares the same PEP 723 dependency and runs the same way,
# `uv run --script`. The job that calls it never `uv sync`s.
# /// script
# requires-python = ">=3.11"
# dependencies = ["packaging>=25"]
# ///
"""Fail a change set that moves a published PyPI-lane member without bumping its version.

The platform lane embeds internal libraries from source at the release commit (ADR-0004),
so a lane member can change, merge, and run in production while PyPI keeps serving that
same version number with the old content — `hexkit 9.0.1` denoting two different things,
permanently, with no consumer ever told theirs is behind. `stamp_platform_version.py`
labels the image's copy `+ghga.<version>` so SBOM metadata stays coherent, but labelling a
divergence is not preventing one. This is the check that prevents it.

The rule: **a member whose shipped content changed must declare a version the index does
not already serve.** Which is to say it must be a release candidate — the same test
`pypi_members.release_candidates` applies to a tag, asked here of a diff instead. Not
merely "absent from the index": a member trailing the index could clear that with a bump
the release plan would still skip, leaving the drift unpublishable and so unresolved.

Shipped content means the member's packaged roots plus its `pyproject.toml`, whose
`[project]` table becomes the METADATA. Changes under `tests/` or to a README ship nothing
to consumers and demand no bump.

A bump does not claim the change was significant — semver's major/minor/patch carries
that, and the author still chooses it. It asserts only that this content is not the content
already published. Nothing is released on merge either: publishing still needs a pushed
tag, so bumps accumulate and one run ships them together.

Usage (`uv run --script`, so the PEP 723 block above resolves):
    git diff --name-only origin/main...HEAD | uv run --script scripts/pypi_drift.py
    git diff --name-only origin/main...HEAD | uv run --script scripts/pypi_drift.py --list
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import tomllib

from pypi_members import pypi_members, release_candidates

ROOT = pathlib.Path(__file__).resolve().parents[1]


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


def changed_members(files: list[str]) -> list[str]:
    """Selects the lane members whose shipped content `files` touches.

    Deliberately not `affected_targets.affected()`, which answers "what might this break?"
    and is right to over-approximate: it expands to dependents — whose own distributions
    do not change when a dependency does — and treats repo-wide paths such as `scripts/`
    or `.github/workflows/` as touching every member, none of which ship inside a wheel.
    Reusing it here would demand a version bump of every lane member for a workflow edit.

    Args:
        files: Changed file paths, relative to the repo root.

    Returns:
        The sorted member folders whose shipped content changed, e.g. `["libs/hexkit"]`.

    Raises:
        SystemExit: if any lane member's packaged roots cannot be established. Treating
            one as "ships nothing" would let it drift forever while this check stayed
            green — the failure the check exists to prevent.
    """
    roots = {
        member["path"]: _packaged_roots(member["path"]) for member in pypi_members()
    }
    unknown = sorted(path for path, found in roots.items() if not found)
    if unknown:
        sys.exit(
            "error: cannot establish what these members ship, so drift in them would go"
            f" unnoticed: {', '.join(unknown)}"
        )

    changed = set()
    for path, packaged in roots.items():
        shipped = tuple(f"{path}/{root}/" for root in packaged)
        metadata = f"{path}/pyproject.toml"
        if any(f == metadata or f.startswith(shipped) for f in files):
            changed.add(path)
    return sorted(changed)


def unbumped_members(member_paths: set[str]) -> list[dict]:
    """Finds which of `member_paths` still declare a version the index already serves.

    Args:
        member_paths: The member folders whose shipped content changed.

    Returns:
        The member dicts among them that need a version bump, each carrying the `reason`
        `release_candidates` passed it over for.

    Raises:
        SystemExit: if PyPI cannot be reached, since nothing can be asserted against an
            unknown index.
    """
    candidates, skipped = release_candidates()
    if any(member["index_unreachable"] for member in candidates):
        sys.exit("error: could not reach PyPI to establish what is already released")
    return [member for member in skipped if member["path"] in member_paths]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list",
        action="store_true",
        help="print the lane members the change set ships into and stop, without asking"
        " the index anything",
    )
    args = parser.parse_args(argv)

    changed = changed_members(sys.stdin.read().splitlines())
    if args.list:
        print("\n".join(changed))
        return 0
    if not changed:
        print("no PyPI-lane member's shipped content changed")
        return 0

    print("changed lane members: " + ", ".join(changed))
    needing_a_bump = unbumped_members(set(changed))
    for member in needing_a_bump:
        print(
            f"{member['package']}: {member['reason']}, but its shipped content changed"
            " — bump it, or the platform and PyPI disagree about what that version"
            " contains",
            file=sys.stderr,
        )
    return 1 if needing_a_bump else 0


if __name__ == "__main__":
    sys.exit(main())
