"""SessionStart hook: warn when the clone has no pre-commit hook installed.

The dev container installs it in post-create, but a clone that skipped that step
commits without the checks CI runs, and nothing says so. Prints nothing when the
hook is there, on the host (the container check covers that) and in CI.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from host import on_host

FOR_DEV = (
    "The git hooks are not installed in this clone, so commits skip pre-commit."
    " Run: just hooks"
)
FOR_AGENT = (
    "The git hooks are not installed in this clone, so a commit would skip the"
    " pre-commit checks. Tell the dev, and run `just hooks` before you commit."
)


def hook_installed(cwd: Path) -> bool:
    """Whether git would find a pre-commit hook; True when git cannot tell."""
    try:
        found = subprocess.run(
            ["git", "rev-parse", "--git-path", "hooks/pre-commit"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return True
    return (cwd / found).is_file()


def main() -> int:
    """Print the warning as hook JSON when the hook is missing."""
    if on_host() or os.environ.get("CI"):
        return 0
    cwd = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".")
    if not hook_installed(cwd):
        print(
            json.dumps(
                {
                    "systemMessage": FOR_DEV,
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": FOR_AGENT,
                    },
                }
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
