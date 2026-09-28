"""PreToolUse hook for Bash: block `uv` on the host.

`.venv` is bind-mounted between host and container, so a host-side `uv` leaves the
container an interpreter symlink that does not resolve. The `just` recipes refuse to
run on the host; this stops an agent from calling `uv` directly to get past them.
"""

from __future__ import annotations

import json
import re
import sys

from host import on_host

# `uv` as a command word: at the start, after a separator or `$(`, and after any
# leading VAR=value assignments. `uvx` and paths containing "uv" do not match.
UV_COMMAND = re.compile(r"(?:^|[;&|(`\n]|\$\()\s*(?:\w+=\S*\s+)*uv(?=\s|$)")

MESSAGE = (
    "Blocked: `uv` must not run on the host, where it breaks the dev container's"
    " .venv (README: 'Work inside the dev container'). Use the just recipe inside the"
    " container instead (just sync, just lock, just test <member>, ...), or ask the"
    " dev. GHGA_ALLOW_HOST=1 overrides this for a deliberate bare-host run."
)


def runs_uv(command: str) -> bool:
    """Whether the shell command runs `uv` as a command."""
    return UV_COMMAND.search(command) is not None


def main() -> int:
    """Exit 2 when the Bash command runs `uv` on the host."""
    if not on_host():
        return 0
    command = json.load(sys.stdin).get("tool_input", {}).get("command", "")
    if runs_uv(command):
        print(MESSAGE, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
