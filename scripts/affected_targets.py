#!/usr/bin/env python3
"""Compute the workspace targets affected by a change set.

Generalises the legacy `get_affected_services.py` to the whole monorepo: a change under a
member directory affects that member; a change to a repo-wide file (root pyproject/lock,
toolchain, shared Dockerfile, CI, scripts, or the shared chart library) affects *everything*.

Usage:
    python scripts/affected_targets.py [--base origin/main] [--format json|lines|matrix]

Output (json, default):
    {"all": false, "targets": ["libs/hexkit", "services/auth-service"]}

stdlib only — runs under plain python or `uv run`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Directories whose subdirectories are individually-buildable targets.
TARGET_ROOTS = ("libs", "services", "tools", "frontend", "deploy/charts")
# Single-directory targets (not split into members).
LEAF_TARGETS = ("testbed",)

# A change touching any of these affects ALL targets (repo-wide concerns).
GLOBAL_PREFIXES = (
    "pyproject.toml", "uv.lock", ".python-version", "justfile",
    ".pre-commit-config.yaml", ".dockerignore",
    "docker/", "scripts/", ".github/workflows/",
    # the shared chart library underpins every generated chart:
    "deploy/charts/ghga-common/",
)


def changed_files(base: str) -> list[str]:
    """Return files changed vs `base` (merge-base diff), else fall back to the working tree."""
    def run(args: list[str]) -> list[str] | None:
        try:
            out = subprocess.run(
                ["git", "-C", str(REPO), *args],
                capture_output=True, text=True, check=True,
            ).stdout
        except subprocess.CalledProcessError:
            return None
        return [line for line in out.splitlines() if line.strip()]

    # base...HEAD (three-dot = changes since the merge base)
    if run(["rev-parse", "--verify", "--quiet", base]) is not None:
        diff = run(["diff", "--name-only", f"{base}...HEAD"])
        if diff is not None:
            return diff
    # Fallbacks: committed-but-unmerged + uncommitted working tree.
    files: set[str] = set()
    for args in (["diff", "--name-only", "HEAD"], ["ls-files", "--others", "--exclude-standard"]):
        got = run(args)
        if got:
            files.update(got)
    return sorted(files)


def affected(files: list[str]) -> tuple[bool, list[str]]:
    """Map changed files to (all?, sorted target list)."""
    if any(f.startswith(GLOBAL_PREFIXES) for f in files):
        return True, all_targets()
    hit: set[str] = set()
    for f in files:
        parts = f.split("/")
        for root in TARGET_ROOTS:
            depth = root.count("/") + 1
            if f.startswith(root + "/") and len(parts) > depth:
                hit.add("/".join(parts[: depth + 1]))
        for leaf in LEAF_TARGETS:
            if f == leaf or f.startswith(leaf + "/"):
                hit.add(leaf)
    return False, sorted(hit)


def all_targets() -> list[str]:
    """Every present target (a member dir with a build manifest)."""
    found: set[str] = set()
    for root in TARGET_ROOTS:
        base = REPO / root
        if not base.is_dir():
            continue
        for member in sorted(p for p in base.iterdir() if p.is_dir()):
            if any((member / m).exists() for m in ("pyproject.toml", "package.json", "Chart.yaml")):
                found.add(f"{root}/{member.name}")
    for leaf in LEAF_TARGETS:
        if (REPO / leaf).is_dir():
            found.add(leaf)
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="origin/main", help="base ref to diff against")
    ap.add_argument("--format", choices=("json", "lines", "matrix"), default="json")
    args = ap.parse_args(argv)

    is_all, targets = affected(changed_files(args.base))

    if args.format == "lines":
        print("\n".join(targets))
    elif args.format == "matrix":  # GitHub Actions: {"target": [...]}
        print(json.dumps({"target": targets}))
    else:
        print(json.dumps({"all": is_all, "targets": targets}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
