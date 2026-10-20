"""PreToolUse hook for Edit, Write and NotebookEdit: block edits to generated files.

Exits 2 with the command that regenerates the file. The ADR and epic indexes and
the README parameter lists sit inside hand-edited files, so `docs_check.py` and the
service-docs pre-commit hook keep them, not this hook.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path, PurePosixPath

SCRIPTS = Path(__file__).resolve().parents[1]
REPO = SCRIPTS.parent

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

# The files scripts/service_docs.py writes, named as it names them. Importing it would
# pull in FastAPI, so the test checks that the names match.
MEMBER_TIERS = ("libs", "services", "tools")
SCHEMA_FILE = "config_schema.json"
EXAMPLE_FILE = "example_config.yaml"
OPENAPI_FILE = "openapi.yaml"
SERVICE_DOCS_HOW = (
    "change the Config class, the routes or dev_config.yaml, then run just service-docs"
)


def checkout_of(path: Path) -> Path | None:
    """The checkout that encloses the path, which may be a worktree."""
    for parent in path.parents:
        if (parent / ".git").exists():
            return parent
    return None


def generated_charts() -> set[str]:
    """The charts create_charts.py stamps: one per image member."""
    sys.path.insert(0, str(SCRIPTS))
    try:
        from image_members import image_members
    except ImportError:  # tomllib needs Python 3.11; a host may have an older one
        return set()
    return {member["package"] for member in image_members()}


def service_doc(rel: PurePosixPath, root: Path) -> bool:
    """Whether service_docs.py writes the file.

    It takes part for a member with a config schema, and writes the OpenAPI
    specification only where one exists already.
    """
    parts = rel.parts
    if len(parts) != 3 or parts[0] not in MEMBER_TIERS:
        return False
    member = root / parts[0] / parts[1]
    if not (member / SCHEMA_FILE).is_file():
        return False
    if rel.name == OPENAPI_FILE:
        return (member / OPENAPI_FILE).is_file()
    return rel.name in (SCHEMA_FILE, EXAMPLE_FILE)


def regenerate_with(rel: PurePosixPath, root: Path = REPO) -> str | None:
    """How to regenerate the file in the checkout, or None when it is edited by hand."""
    if str(rel) in FIXED:
        return FIXED[str(rel)]
    parts = rel.parts
    if len(parts) > 3 and parts[:2] == ("deploy", "charts"):
        if parts[2] in generated_charts():
            return CHARTS_HOW
    if service_doc(rel, root):
        return SERVICE_DOCS_HOW
    return None


def main() -> int:
    """Exit 2 when the tool call writes a generated file."""
    tool_input = json.load(sys.stdin).get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path", "")
    path = Path(file_path.replace("\\", "/"))
    root = checkout_of(path) if file_path else None
    if root is None:
        return 0
    rel = PurePosixPath(path.relative_to(root).as_posix())
    how = regenerate_with(rel, root)
    if how:
        print(
            f"Blocked: {rel} is generated; do not edit it by hand. Instead, {how}.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
