"""SessionStart hook: warn when an agent session runs outside the dev container.

Prints nothing in the container and in CI. On the host it tells the dev (via
`systemMessage`) and the agent (via `additionalContext`) before the first command,
instead of at the first `just` error or a broken `.venv`.
"""

from __future__ import annotations

import json
import sys

from host import on_host

FOR_DEV = (
    "This agent session runs on the host, outside the dev container. The just recipes"
    " will refuse to run; reopen the folder in the container."
)
FOR_AGENT = (
    "This session runs on the host, outside the dev container (/.dockerenv is"
    " missing, CI and GHGA_ALLOW_HOST are unset). The just recipes will refuse to run,"
    " and running uv here breaks the container's .venv. Tell the dev, and ask before"
    " running any repo tooling."
)


def main() -> int:
    """Print the warning as hook JSON when on the host."""
    if on_host():
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
