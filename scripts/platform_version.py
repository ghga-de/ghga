#!/usr/bin/env python3
"""Derive the platform version of a checkout from its nearest `ghga/` tag (ADR-0046).

At a tag this is the tag's version; after one, the commits since it and the abbreviated
SHA follow as build metadata, and local changes add `dirty`. Without git or a matching
tag it is `0.0.0+dev`. docs/releases.md defines the format.

`ghga_datasteward_kit/__init__.py` and the front end's `run.js` carry their own copies of
this rule, since none of the three can import the others; change them together.

A CD build of `dev` (ADR-0045) needs a version that rises with every run instead, which
build metadata does not give: `--cd <number>` appends the run's number as a dev release
to the highest `ghga/` tag the commit contains.

Usage:
    python3 scripts/platform_version.py           # e.g. 15.3.1-rc.8+dev.71.44594f5
    python3 scripts/platform_version.py --cd 19401  # e.g. 15.3.1-rc.8.dev.19401

stdlib only.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

FALLBACK = "0.0.0+dev"

# `git describe --abbrev=7 --dirty` output, e.g. ghga/15.3.1-rc.8-71-g44594f5-dirty
DESCRIBE = re.compile(
    r"^ghga/(?P<tag>.+?)(?:-(?P<count>\d+)-g(?P<sha>[0-9a-f]+))?(?P<dirty>-dirty)?$"
)

# A platform version as the tags spell it, e.g. 15.3.1 or 15.3.1-rc.8
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")

ROOT = Path(__file__).resolve().parents[1]


def from_describe(described: str) -> str:
    """Turns `git describe` output into a semver platform version."""
    match = DESCRIBE.match(described)
    if not match:
        return FALLBACK
    build = []
    if match["count"]:
        build += ["dev", match["count"], match["sha"]]
    if match["dirty"]:
        build.append("dirty")
    return match["tag"] + ("+" + ".".join(build) if build else "")


def _precedence(version: str) -> tuple:
    """A sort key following semver precedence: a release above its prereleases."""
    major, minor, patch, pre = SEMVER.match(version).groups()  # type: ignore[union-attr]
    identifiers = tuple(
        (0, int(part), "") if part.isdigit() else (1, 0, part)
        for part in (pre.split(".") if pre else ())
    )
    return int(major), int(minor), int(patch), pre is None, identifiers


def cd_version(tags: list[str], number: int) -> str:
    """The version of a CD build: a dev release after the highest of `tags`.

    The highest tag rather than the nearest, which `git describe` picks: a hotfix merged
    back into `dev` can bring a final tag nearer than the newer candidate already there,
    and the version must never go down. A final tag is followed by a dev release of the
    next patch, since `15.3.1-dev.N` would sort below the release it follows.
    """
    versions = [
        tag.removeprefix("ghga/")
        for tag in tags
        if tag.startswith("ghga/") and SEMVER.match(tag.removeprefix("ghga/"))
    ]
    if not versions:
        return f"0.0.0-dev.{number}"
    highest = max(versions, key=_precedence)
    major, minor, patch, pre = SEMVER.match(highest).groups()  # type: ignore[union-attr]
    if pre:
        return f"{highest}.dev.{number}"
    return f"{major}.{minor}.{int(patch) + 1}-dev.{number}"


def _git(cwd: Path, *args: str) -> str | None:
    """Runs git and returns its output, or None when git is missing or fails."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    return None if result.returncode else result.stdout.strip()


def platform_version(cwd: Path = ROOT) -> str:
    """The platform version of the checkout containing `cwd`."""
    described = _git(
        cwd, "describe", "--tags", "--match", "ghga/*", "--dirty", "--abbrev=7"
    )
    return FALLBACK if described is None else from_describe(described)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cd", type=int, metavar="NUMBER", help="the version of CD build NUMBER"
    )
    args = parser.parse_args(argv)
    if args.cd is None:
        print(platform_version())
    else:
        tags = _git(ROOT, "tag", "--merged", "HEAD", "--list", "ghga/*") or ""
        print(cd_version(tags.split(), args.cd))


if __name__ == "__main__":
    main()
