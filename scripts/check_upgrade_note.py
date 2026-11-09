#!/usr/bin/env python3
"""Check that a pull request description says what an upgrade requires.

A pull request that changes a config schema, an example config, an `openapi.yaml` or
chart values needs a line starting with `Upgrade:`: one per action a deployment or a
tool's user must take, or `Upgrade: none`. Elsewhere the line is optional, for actions
no such file shows, like a renamed CLI flag. The release notes collect these lines from
the descriptions (scripts/release_notes.py), so they are written once, while the release
they land in is still unknown. Used by .github/workflows/upgrade-note.yaml, a required
check, so a missing line blocks the merge.

Release merges and back-merges between `dev` and `main`, and the branches Renovate and
the security scan own, are exempt. Without `--changed`, every pull request needs the
line, so a broken diff cannot let one through.

Usage:
    git diff --name-only <base> <head> | python3 scripts/check_upgrade_note.py \
        --head <branch> --base <branch> --changed - -- "<body>"
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path, PurePosixPath

RULES = "docs/conventions.md#names-branches-prs-commits"

EXEMPT_HEADS = ("renovate/", "automated/")
INTEGRATION_BRANCHES = {"dev", "main"}

# What a deployment reads; `config_schema.json` and `openapi.yaml` are generated from the
# code, so they change whenever a setting or a route does.
UPGRADE_FILES = {
    "config_schema.json",
    "example_config.yaml",
    "openapi.yaml",
    "chart-values.yaml",
}
# The charts the deployments install. `ghga-demo` and `aai`, and the `values-local.yaml`
# and the like, serve only the demo and the test bed.
CHART_VALUES = re.compile(r"deploy/charts/(?!ghga-demo/|aai/)[^/]+/values\.yaml")

# A long line may continue on lines that start with whitespace, as git folds trailers.
UPGRADE_LINE = re.compile(
    r"^Upgrade:[ \t]*(?P<text>\S.*(?:\n[ \t]+\S.*)*)", re.MULTILINE
)
# The template explains the line inside a comment, which must not count as one.
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
NONE = "none"


def is_exempt(head: str, base: str) -> bool:
    """Return whether a PR from `head` into `base` is exempt from the check."""
    release_merge = {head, base} == INTEGRATION_BRANCHES
    return head.startswith(EXEMPT_HEADS) or release_merge


def needs_note(paths: list[str]) -> list[str]:
    """Return the changed files that make an `Upgrade:` line required."""
    return [
        path
        for path in paths
        if PurePosixPath(path).name in UPGRADE_FILES or CHART_VALUES.fullmatch(path)
    ]


def read_paths(source: str) -> list[str]:
    """Return the paths in the file `source`, one per line, `-` meaning stdin."""
    if source == "-":
        return sys.stdin.read().splitlines()
    return Path(source).read_text(encoding="utf-8").splitlines()


def upgrade_lines(text: str) -> list[str]:
    """Return the text of each `Upgrade:` line, `none` included, folds joined."""
    text = COMMENT.sub("", text.replace("\r\n", "\n"))
    return [" ".join(m["text"].split()) for m in UPGRADE_LINE.finditer(text)]


def upgrade_notes(text: str) -> list[str]:
    """Return the actions an upgrade requires, leaving out `Upgrade: none`."""
    return [line for line in upgrade_lines(text) if line.lower().rstrip(".") != NONE]


def main(argv: list[str] | None = None) -> int:
    """Fail if the PR needs an `Upgrade:` line and its description has none."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--head", default="", help="the PR's head branch")
    parser.add_argument("--base", default="", help="the PR's base branch")
    parser.add_argument(
        "--changed", help="a file of the PR's changed paths, one per line; - for stdin"
    )
    parser.add_argument("body")
    args = parser.parse_args(argv)

    if is_exempt(args.head, args.base):
        print(f"Exempt: {args.head} into {args.base}.")
        return 0
    lines = upgrade_lines(args.body)
    if lines:
        print(*(f"Upgrade: {line}" for line in lines), sep="\n")
        return 0
    triggers = needs_note(read_paths(args.changed)) if args.changed else None
    if triggers == []:
        print("No upgrade note needed: no config, API or chart values changed.")
        return 0

    problem = (
        "The description needs a line starting with `Upgrade:` for each action an"
        " upgrade requires, or `Upgrade: none`."
    )
    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    print(f"::error title=Upgrade note::{problem}" if in_actions else problem)
    print(f"See {RULES}.")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write(f"**Missing upgrade note.** {problem} See `{RULES}`.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
