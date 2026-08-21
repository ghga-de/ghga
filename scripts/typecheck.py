#!/usr/bin/env python3
"""Run mypy the way this workspace requires: once per unit, never per file.

mypy's answer depends on the *set* of paths it is handed, so "type-check the changed
files" is not a well-defined operation here:

  - `mypy services/dcs/src` is clean, but `mypy libs/ghga-event-schemas/src
    services/dcs/src` reports an incompatible-argument error in dcs. Widening the path
    set changes how imports resolve, so a file list spanning two members invents errors
    that neither member has on its own.
  - `mypy .` cannot run at all: 24 members carry a `tests` package, and the duplicate
    module names abort the run before anything is checked.

So the unit -- not the file -- is the thing that gets checked: a member is checked as
`<member>/src` plus its test package(s), in ONE invocation (checking a test tree on its
own resolves its imports differently and reports ~2x the errors). Given file arguments,
this checks every unit that owns one of them; with --all, every unit.

Used by the pre-commit hook, by `just typecheck`, and by CI, so all three agree.

The unit mapping deliberately does NOT match `affected_targets.py`, which drives CI's
build matrix: that one adds the reverse-dependency closure (a change to hexkit re-checks
every dependent) and covers non-Python targets. Here the closure is CI's job -- a commit
hook checks what you touched.

Usage:
    python scripts/typecheck.py [--all | <path> ...]

stdlib only -- runs under plain python or `uv run`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Directories whose subdirectories are workspace members (each with a pyproject.toml).
MEMBER_ROOTS = ("libs", "services", "tools")
# Python outside the workspace: not members, but ours and type-checked all the same.
STANDALONE_UNITS = ("deploy/src", "scripts", "testbed")


def all_units() -> list[str]:
    """Every unit present in the tree."""
    units = [
        f"{root}/{member.name}"
        for root in MEMBER_ROOTS
        if (REPO / root).is_dir()
        for member in sorted((REPO / root).iterdir())
        if (member / "pyproject.toml").is_file()
    ]
    units += [unit for unit in STANDALONE_UNITS if (REPO / unit).is_dir()]
    return sorted(units)


def units_for(files: Iterable[str]) -> list[str]:
    """Map paths to the units owning them. Paths in no unit are skipped.

    Skipping is deliberate: `frontend/data-portal/src/assets/schemas/*.py` are excluded
    from the shared ruff/mypy config and belong to no unit, and a commit touching only
    such a file has nothing to type-check.
    """
    known = set(all_units())
    hit = set()
    for file in files:
        parts = Path(file).as_posix().split("/")
        # units are one or two path components deep ("scripts", "libs/hexkit")
        hit.update({"/".join(parts[:depth]) for depth in (1, 2)} & known)
    return sorted(hit)


def unit_paths(unit: str) -> list[str]:
    """The paths handed to a single mypy invocation for `unit`."""
    if unit in STANDALONE_UNITS:
        return [unit]
    directory = REPO / unit
    paths = [f"{unit}/src"] if (directory / "src").is_dir() else []
    # members name their test package `tests`, or `tests_<name>` where a plain `tests`
    # would collide with a sibling's under a shared pytest rootdir
    paths += sorted(
        f"{unit}/{path.name}"
        for path in directory.iterdir()
        if path.is_dir() and (path.name == "tests" or path.name.startswith("tests_"))
    )
    return paths


def check(units: list[str]) -> int:
    """Run mypy once per unit; return the number of units that failed."""
    failed = []
    for unit in units:
        paths = unit_paths(unit)
        if not paths:
            continue
        print(f"== mypy {' '.join(paths)} ==", flush=True)
        # `-m mypy` rather than a bare `mypy`, so this works under a plain interpreter
        # from the workspace venv as well as under `uv run`
        if subprocess.run([sys.executable, "-m", "mypy", *paths], cwd=REPO).returncode:
            failed.append(unit)
    if failed:
        print(f"\nmypy failed in: {', '.join(failed)}", file=sys.stderr)
    return len(failed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths", nargs="*", help="changed files; their units are checked"
    )
    parser.add_argument("--all", action="store_true", help="check every unit")
    args = parser.parse_args(argv)

    if args.all:
        units = all_units()
    elif args.paths:
        units = units_for(args.paths)
    else:
        parser.error("pass file paths, or --all")

    return 1 if check(units) else 0


if __name__ == "__main__":
    sys.exit(main())
