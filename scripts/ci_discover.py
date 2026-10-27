#!/usr/bin/env python3
"""Compute what ci.yaml's `discover` job hands its matrix jobs, as GITHUB_OUTPUT lines.

    python3 scripts/ci_discover.py --base origin/dev >> "$GITHUB_OUTPUT"

Outputs:

- `python`, `frontend`: the affected targets under those roots, as JSON lists.
  testbed and deploy targets are exercised by the integration gate instead.
- `image-builds`: image name -> `just` build recipe, for each image whose Dockerfile
  changed; `images`: its keys, so a skipped matrix job's check is titled plainly.
- `devcontainer`: `true` when `.devcontainer/` changed.

A base that does not resolve (branch creation, force push) means an unknown change set,
and that must mean "check everything", never "check nothing".
"""

import argparse
import json
import sys

from affected_targets import BaseRefError, affected, all_targets, changed_files
from image_members import image_members


def split(targets: list[str], *roots: str) -> list[str]:
    """The targets whose top-level directory is one of `roots`."""
    return [t for t in targets if t.split("/")[0] in roots]


def image_builds(changed: list[str] | None, members: list[dict]) -> dict[str, str]:
    """Map each image to build to its `just` recipe; `changed=None` builds every image.

    Read from the raw diff, not from the affected targets: `docker/` is a repo-wide prefix
    there, so every global change (uv.lock, a workflow, scripts/) expands to all targets
    and would look like a base-image change. The Python members all share
    docker/Dockerfile, so they are covered by the one mono build.
    """
    builds: dict[str, str] = {}
    mono = False
    for member in members:
        if changed is not None and member["dockerfile"] not in changed:
            continue
        if member["kind"] == "python":
            mono = True
        else:
            builds[member["package"]] = "image " + member["path"]
    return {"platform": "image-mono", **builds} if mono else builds


def discover(base: str) -> dict[str, str]:
    """The `discover` outputs for the change set since the merge base with `base`."""
    changed: list[str] | None = None
    if base:
        try:
            changed = changed_files(base)
        except BaseRefError:
            changed = None
    targets = all_targets() if changed is None else affected(changed)[1]
    builds = image_builds(changed, image_members())
    devcontainer = changed is None or any(
        f.startswith(".devcontainer/") for f in changed
    )
    return {
        "python": json.dumps(split(targets, "libs", "services", "tools")),
        "frontend": json.dumps(split(targets, "frontend")),
        "images": json.dumps(list(builds)),
        "image-builds": json.dumps(builds),
        "devcontainer": json.dumps(devcontainer),
    }


def main(argv: list[str] | None = None) -> int:
    """Print the outputs as `key=value` lines."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="", help="base ref; empty checks everything")
    args = parser.parse_args(argv)
    for key, value in discover(args.base).items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
