"""The host test the justfile's `_guard-host` applies, shared by the agent hooks."""

from __future__ import annotations

import os
from pathlib import Path

DOCKERENV = Path("/.dockerenv")


def on_host() -> bool:
    """Whether this runs outside the dev container, with no exemption set.

    CI runs the recipes on a bare runner by design, and GHGA_ALLOW_HOST is the
    deliberate escape hatch, so both count as not being on the host.
    """
    if os.environ.get("CI") or os.environ.get("GHGA_ALLOW_HOST"):
        return False
    return not DOCKERENV.exists()
