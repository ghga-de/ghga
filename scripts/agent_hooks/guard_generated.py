"""PreToolUse hook for Edit and Write: block edits to generated files.

Exits 2 with the command that regenerates the file. The ADR and epic indexes sit
inside hand-edited files, so `docs_check.py` keeps them, not this hook.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path, PurePosixPath

SCRIPTS = Path(__file__).resolve().parents[1]

FIXED = {
    "uv.lock": "just lock",
    "frontend/data-portal/pnpm-lock.yaml": "pnpm install in frontend/data-portal",
    "deploy/charts/ghga-demo/values-mono.yaml": "just charts",
    "deploy/charts/ghga-demo/values-artifacts.yaml": "just testbed-artifacts",
}
CHARTS_HOW = (
    "change the member's chart-values.yaml or the generator in deploy/src/, then"
    " run just charts"
)


def repo_relative(file_path: str) -> PurePosixPath | None:
    """The path relative to the enclosing checkout, which may be a worktree."""
    path = Path(file_path.replace("\\", "/"))
    for parent in path.parents:
        if (parent / ".git").exists():
            return PurePosixPath(path.relative_to(parent).as_posix())
    return None


def generated_charts() -> set[str]:
    """The charts create_charts.py stamps: one per image member."""
    sys.path.insert(0, str(SCRIPTS))
    try:
        from image_members import image_members
    except ImportError:  # tomllib needs Python 3.11; a host may have an older one
        return set()
    return {member["package"] for member in image_members()}


def regenerate_with(rel: PurePosixPath) -> str | None:
    """How to regenerate the file, or None when it is edited by hand."""
    if str(rel) in FIXED:
        return FIXED[str(rel)]
    parts = rel.parts
    if len(parts) > 3 and parts[:2] == ("deploy", "charts"):
        if parts[2] in generated_charts():
            return CHARTS_HOW
    return None


def main() -> int:
    """Exit 2 when the tool call writes a generated file."""
    file_path = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
    rel = repo_relative(file_path) if file_path else None
    how = regenerate_with(rel) if rel else None
    if how:
        print(
            f"Blocked: {rel} is generated; do not edit it by hand. Instead, {how}.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
