#!/usr/bin/env python3
"""Derive the platform version of a checkout from its nearest `ghga/` tag (ADR-0046).

At a tag this is the tag's version; after one, the commits since it and the abbreviated
SHA follow as build metadata, and local changes add `dirty`. Without git or a matching
tag it is `0.0.0+dev`. docs/releases.md defines the format.

`ghga_datasteward_kit/__init__.py` and the front end's `run.js` carry their own copies of
this rule, since none of the three can import the others; change them together.

Usage:
    python3 scripts/platform_version.py     # e.g. 15.3.1-rc.8+dev.71.44594f5

stdlib only.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

FALLBACK = "0.0.0+dev"

# `git describe --abbrev=7 --dirty` output, e.g. ghga/15.3.1-rc.8-71-g44594f5-dirty
DESCRIBE = re.compile(
    r"^ghga/(?P<tag>.+?)(?:-(?P<count>\d+)-g(?P<sha>[0-9a-f]+))?(?P<dirty>-dirty)?$"
)

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


def platform_version(cwd: Path = ROOT) -> str:
    """The platform version of the checkout containing `cwd`."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--match", "ghga/*", "--dirty", "--abbrev=7"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return FALLBACK
    if result.returncode:
        return FALLBACK
    return from_describe(result.stdout.strip())


if __name__ == "__main__":
    print(platform_version())
