#!/usr/bin/env python3
"""Compute the workspace targets affected by a change set.

Generalises the legacy `get_affected_services.py` to the whole monorepo: a change under a
member directory affects that member; a change to a repo-wide file (root pyproject/lock,
toolchain, shared Dockerfile, CI, scripts, or the shared chart library) affects *everything*.

Unlike the FSB original (where services never depend on each other and shared libs arrive
via the repo-wide lock), this workspace source-couples internal libraries — so a change to
a lib affects every member that (transitively) depends on it. The dependency graph is
derived from the members' own pyproject.toml files: any dependency whose (normalised) name
is another workspace member counts as an internal edge.

Usage:
    python scripts/affected_targets.py [--base origin/main] [--format json|lines|matrix]

Output (json, default):
    {"all": false, "targets": ["libs/hexkit", "services/auth-service"]}

stdlib only (python >= 3.11 for tomllib) — runs under plain python or `uv run`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import tomllib

REPO = Path(__file__).resolve().parents[1]

# Directories whose subdirectories are individually-buildable targets.
TARGET_ROOTS = ("libs", "services", "tools", "frontend", "deploy/charts")
# Single-directory targets (not split into members).
LEAF_TARGETS = ("testbed",)

# A change touching any of these affects ALL targets (repo-wide concerns).
GLOBAL_PREFIXES = (
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "justfile",
    ".pre-commit-config.yaml",
    ".dockerignore",
    "docker/",
    "scripts/",
    ".github/workflows/",
    # the shared chart library underpins every generated chart:
    "deploy/charts/ghga-common/",
)


def changed_files(base: str) -> list[str]:
    """Return files changed vs `base` (merge-base diff), else fall back to the working tree."""

    def run(args: list[str]) -> list[str] | None:
        try:
            out = subprocess.run(
                ["git", "-C", str(REPO), *args],
                capture_output=True,
                text=True,
                check=True,
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
    for args in (
        ["diff", "--name-only", "HEAD"],
        ["ls-files", "--others", "--exclude-standard"],
    ):
        got = run(args)
        if got:
            files.update(got)
    return sorted(files)


def affected(files: list[str]) -> tuple[bool, list[str]]:
    """Map changed files to (all?, sorted target list), including dependents."""
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
    return False, sorted(with_dependents(hit))


def _canonical(name: str) -> str:
    """PEP-503-style package-name normalisation."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_name(spec: str) -> str:
    """Extract the bare package name from a PEP-508 requirement string."""
    return _canonical(re.split(r"[\s\[<>=!~;(@]", spec.strip(), maxsplit=1)[0])


def internal_dep_graph() -> dict[str, set[str]]:
    """Map each Python member target to the member targets it depends on.

    An edge exists when a member's pyproject declares a dependency (regular or
    extra) whose normalised name is another workspace member's project name.
    Workspace-internal deps are source-coupled, so a change to the dependency
    must re-check the dependent.
    """
    name_to_target: dict[str, str] = {}
    raw_deps: dict[str, list[str]] = {}
    for target in all_targets():
        manifest = REPO / target / "pyproject.toml"
        if not manifest.is_file():
            continue
        project = tomllib.loads(manifest.read_text()).get("project", {})
        name = project.get("name")
        if not name:
            continue
        name_to_target[_canonical(name)] = target
        deps = list(project.get("dependencies", []))
        for extra in project.get("optional-dependencies", {}).values():
            deps.extend(extra)
        raw_deps[target] = deps
    return {
        target: {
            name_to_target[dep]
            for dep in map(_requirement_name, deps)
            if dep in name_to_target and name_to_target[dep] != target
        }
        for target, deps in raw_deps.items()
    }


def with_dependents(targets: set[str]) -> set[str]:
    """Expand a target set with everything that transitively depends on it."""
    dependents: dict[str, set[str]] = {}
    for member, deps in internal_dep_graph().items():
        for dep in deps:
            dependents.setdefault(dep, set()).add(member)
    result = set(targets)
    queue = list(targets)
    while queue:
        for member in dependents.get(queue.pop(), ()):
            if member not in result:
                result.add(member)
                queue.append(member)
    return result


def all_targets() -> list[str]:
    """Every present target (a member dir with a build manifest)."""
    found: set[str] = set()
    for root in TARGET_ROOTS:
        base = REPO / root
        if not base.is_dir():
            continue
        for member in sorted(p for p in base.iterdir() if p.is_dir()):
            if any(
                (member / m).exists()
                for m in ("pyproject.toml", "package.json", "Chart.yaml")
            ):
                found.add(f"{root}/{member.name}")
    for leaf in LEAF_TARGETS:
        if (REPO / leaf).is_dir():
            found.add(leaf)
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="origin/main", help="base ref to diff against")
    ap.add_argument("--format", choices=("json", "lines", "matrix"), default="json")
    ap.add_argument(
        "--all",
        action="store_true",
        help="skip diffing and emit every target (CI fallback when no base resolves"
        " — an unknown change set must mean 'check everything', never 'check nothing')",
    )
    args = ap.parse_args(argv)

    if args.all:
        is_all, targets = True, all_targets()
    else:
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
