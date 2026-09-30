"""PostToolUse hook for Edit and Write: format the Python file that was just edited.

Runs the ruff of the checkout that holds the file, the repo or one of its worktrees
under .claude/worktrees/, so its root pyproject.toml applies. Silent and exit 0
in every case: the edit has happened, and what ruff cannot fix, such as an import
not used yet, is for `just lint` to report once the edit is done.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from guard_generated import REPO, checkout_of
from host import on_host

TIMEOUT = 20  # seconds per ruff call; the hook itself gets 30 in the settings


def ruff_calls(path: Path) -> list[list[str]]:
    """The ruff commands for the file, or none when there is nothing to do.

    `--force-exclude` keeps ruff away from the files the root config excludes, which
    it would otherwise format when named on the command line.
    """
    if path.suffix != ".py" or not path.is_relative_to(REPO) or on_host():
        return []
    root = checkout_of(path)
    ruff = root / ".venv" / "bin" / "ruff" if root else None
    if ruff is None or not ruff.is_file() or not path.is_file():
        return []
    return [
        [str(ruff), "format", "--force-exclude", "--quiet", str(path)],
        [str(ruff), "check", "--fix", "--force-exclude", "--quiet", str(path)],
    ]


def main() -> int:
    """Format and fix the edited file, ignoring every failure."""
    file_path = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
    if not file_path:
        return 0
    path = Path(file_path).absolute()
    for command in ruff_calls(path):
        try:
            subprocess.run(
                command,
                cwd=checkout_of(path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=TIMEOUT,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
