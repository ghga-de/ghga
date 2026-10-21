"""PostToolUse hook for Edit, Write and Bash: type-check every unit a change can break.

After Edit or Write the edited file counts; after Bash, every .py file the command
wrote, since agents also edit with scripts and `sed`; as a PreToolUse hook on Bash
it marks when the command starts. mypy checks each file's unit and every unit with a
file that imports its module, once per unit as `typecheck.py` does, and ruff checks
the files. Errors go back to the agent before its next tool call; once the units
that failed pass, it says "clean now". It never changes a file and never blocks.

Importers rather than the edited unit alone, because a changed signature breaks
callers in members the agent has not opened; rather than every dependent unit,
because that costs 10-25 s per edit. Re-exports through `__init__` are not followed.
"""

from __future__ import annotations

import fcntl
import json
import re
import subprocess
import sys
from pathlib import Path

from host import on_host

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import typecheck

MAX_LINES = 40
# a branch switch or a rebase rewrites more files than the hook's timeout can check
MAX_FILES = 50
MYPY_ERROR = re.compile(r"^[^:\s]+\.pyi?:\d+(?::\d+)?: error: ")
PYTHON_FILES = (".py", ".pyi")


def git(repo: Path, *args: str) -> str:
    """Run git in the checkout and return its output."""
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout


def module_of(rel: str, unit: str) -> str | None:
    """The dotted module of a file in a unit's `src/`, or None outside it."""
    prefix = f"{unit}/src/"
    if not rel.startswith(prefix):
        return None
    parts = Path(rel[len(prefix) :]).with_suffix("").parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) or None


def importer_pattern(module: str) -> str:
    """An extended regex for the lines that import `module` by name."""
    name = re.escape(module)
    pattern = rf"^\s*(from\s+{name}(\s|\.)|import\s+{name}(\s|,|\.|$))"
    parent, _, last = module.rpartition(".")
    if parent:
        parent = re.escape(parent)
        pattern += rf"|^\s*from\s+{parent}\s+import\s+[^#]*\b{re.escape(last)}\b"
        # the names of a parenthesised import follow on the next lines, out of reach
        # of a line-based grep, so any such import from the parent counts
        pattern += rf"|^\s*from\s+{parent}\s+import\s*\("
    return pattern


def importer_units(repo: Path, module: str) -> set[str]:
    """The units with a Python file that imports `module`."""
    try:
        found = git(
            repo,
            "grep",
            "-l",
            "--untracked",
            "-E",
            importer_pattern(module),
            "--",
            *(f"*{suffix}" for suffix in PYTHON_FILES),
        )
    except subprocess.CalledProcessError:  # exit 1: no match
        return set()
    return set(typecheck.units_for(found.splitlines()))


def changed_since(repo: Path, stamp: Path) -> list[str]:
    """The tracked or untracked Python files modified after the stamp.

    By modification time rather than by `git status`, so a file the command reverted,
    staged or committed counts too. Without a stamp nothing counts.
    """
    if not stamp.exists():
        return []
    since = stamp.stat().st_mtime_ns
    listed = git(
        repo,
        "ls-files",
        "-c",
        "-o",
        "--exclude-standard",
        "--",
        *(f"*{suffix}" for suffix in PYTHON_FILES),
    )
    return sorted(
        {
            rel
            for rel in listed.splitlines()
            if (path := repo / rel).is_file() and path.stat().st_mtime_ns > since
        }
    )


def edited_files(event: dict, repo: Path, stamp: Path) -> list[str]:
    """The Python files the tool call changed, relative to the checkout."""
    if event.get("tool_name") == "Bash":
        return changed_since(repo, stamp)
    path = (event.get("tool_input") or {}).get("file_path") or ""
    try:
        rel = Path(path).resolve().relative_to(repo).as_posix()
    except ValueError:  # outside the checkout
        return []
    return [rel] if rel.endswith(PYTHON_FILES) else []


def units_to_check(files: list[str]) -> set[str]:
    """The units owning the files, plus every unit importing their modules."""
    units: set[str] = set()
    for rel in files:
        for unit in typecheck.units_for([rel]):
            units.add(unit)
            module = module_of(rel, unit)
            if module:
                units |= importer_units(typecheck.REPO, module)
    return units


def run_checks(
    units: set[str], files: list[str], python: str
) -> tuple[list[str], list[str]]:
    """Run mypy on each unit and ruff on the files; return failed units and errors."""
    failed: list[str] = []
    errors: list[str] = []
    for unit in sorted(units):
        if not typecheck.unit_paths(unit):
            continue
        output = typecheck.run_mypy(unit, python, capture=True).stdout
        hits = [line for line in output.splitlines() if MYPY_ERROR.match(line)]
        if hits:
            failed.append(unit)
            errors += hits
    ruff = subprocess.run(
        [python, "-m", "ruff", "check", "--output-format=concise", "--quiet", *files],
        cwd=typecheck.REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    # concise lines start with the path; anything else is a summary
    errors += [line for line in ruff.stdout.splitlines() if line.split(":")[0] in files]
    return failed, errors


def report(
    tool: str, units: set[str], files: list[str], errors: list[str], had_errors: bool
) -> str | None:
    """The text for the agent, or None when there is nothing to say."""
    if not errors and not had_errors:
        return None
    head = (
        f"Type and lint check after this {'command' if tool == 'Bash' else 'edit'}"
        f" (mypy on {', '.join(sorted(units))}; ruff on {', '.join(files)})"
    )
    if not errors:
        return f"{head}: clean now."
    shown = errors[:MAX_LINES]
    more = f"\n... and {len(errors) - MAX_LINES} more" if errors[MAX_LINES:] else ""
    return f"{head}: {len(errors)} error(s).\n" + "\n".join(shown) + more


def check(event: dict, state: Path, stamp: Path, python: str) -> str | None:
    """Check what the tool call changed and return the report."""
    repo = typecheck.REPO
    files = edited_files(event, repo, stamp)
    files = [rel for rel in files if typecheck.units_for([rel])]
    if len(files) > MAX_FILES:
        return None
    units = units_to_check(files)
    if not units:
        return None
    # the units that failed before are checked again, so "clean now" covers them too
    had_errors = state.exists()
    if had_errors:
        units |= set(state.read_text().split())
    failed, errors = run_checks(units, files, python)
    if errors:
        state.write_text(" ".join(failed))
    elif had_errors:
        state.unlink()
    return report(event.get("tool_name") or "", units, files, errors, had_errors)


def main() -> int:
    """Mark a command's start, or print the report as hook JSON.

    Skips where the checks cannot run.
    """
    event = json.load(sys.stdin)
    repo = typecheck.REPO
    python = repo / ".venv/bin/python"
    if on_host() or not python.is_file():
        return 0
    try:
        # per worktree, since `.git` is a file there
        lock, state, stamp = (
            repo / git(repo, "rev-parse", "--git-path", name).strip()
            for name in ("check-units.lock", "check-units.state", "check-units.stamp")
        )
    except (OSError, subprocess.CalledProcessError):  # not a git work tree
        return 0
    if event.get("hook_event_name") == "PreToolUse":
        stamp.touch()
        return 0
    with lock.open("w") as handle:
        # parallel tool calls each run this hook, and mypy's cache takes one writer
        fcntl.flock(handle, fcntl.LOCK_EX)
        text = check(event, state, stamp, str(python))
    if text:
        output = {"hookEventName": "PostToolUse", "additionalContext": text}
        print(json.dumps({"hookSpecificOutput": output}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
