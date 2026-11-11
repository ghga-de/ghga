"""PreToolUse hook for Edit and Write: ask before an edit to lint configuration.

A failing check is fixed in the code, not by weakening the check. The answer is
"ask", not "deny": the dev may want the change, and the root `pyproject.toml` also
holds the dependencies, so only its check tables count there.
"""

from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path, PurePosixPath

from guard_generated import checkout_of

try:
    import tomllib
except ImportError:  # Python before 3.11, on a host: ask for every pyproject.toml edit
    tomllib = None  # type: ignore[assignment]

CHECK_TABLES = ("ruff", "mypy", "pytest", "rumdl")
CONFIG_NAMES = (
    ".pre-commit-config.yaml",
    "ruff.toml",
    ".ruff.toml",
    "mypy.ini",
    ".mypy.ini",
    "pytest.ini",
    "rumdl.toml",
    ".rumdl.toml",
    ".markdownlint*",
    "eslint.config.*",
    ".eslintrc*",
    "prettier.config.*",
    ".prettierrc*",
    ".prettierignore",
)
CONFIG_DIRS = ("frontend/data-portal/eslint-local-rules",)

REASON = (
    "This edit changes {what}. A failing check is fixed in the code, not by"
    " weakening the check; approve only if the dev asked for this change."
)


def after_edit(path: Path, tool_input: dict) -> tuple[str, str] | None:
    """The file's text before and after the edit, or None when the edit cannot apply."""
    before = path.read_text() if path.is_file() else ""
    if "content" in tool_input:
        return before, tool_input["content"]
    old, new = tool_input.get("old_string", ""), tool_input.get("new_string", "")
    if not old or old not in before:
        return None
    count = -1 if tool_input.get("replace_all") else 1
    return before, before.replace(old, new, count)


def changed_tables(before: str, after: str) -> list[str] | None:
    """The check tables that differ, or None when a side is not valid TOML."""
    if tomllib is None:
        return None
    try:
        old_tool = tomllib.loads(before).get("tool", {})
        new_tool = tomllib.loads(after).get("tool", {})
    except tomllib.TOMLDecodeError:
        return None
    return [t for t in CHECK_TABLES if old_tool.get(t) != new_tool.get(t)]


def lint_change(rel: PurePosixPath, path: Path, tool_input: dict) -> str | None:
    """What lint configuration the edit changes, or None."""
    if any(fnmatch.fnmatch(rel.name, pattern) for pattern in CONFIG_NAMES):
        return f"lint configuration ({rel})"
    if any(rel.is_relative_to(directory) for directory in CONFIG_DIRS):
        return f"a local lint rule ({rel})"
    if rel.name != "pyproject.toml":
        return None
    texts = after_edit(path, tool_input)
    if texts is None:
        return None
    tables = changed_tables(*texts)
    if tables is None:
        return f"{rel}, which could not be compared as TOML"
    if not tables:
        return None
    names = ", ".join(f"[tool.{table}]" for table in tables)
    return f"the check configuration in {rel} ({names})"


def main() -> int:
    """Answer "ask" when the tool call changes lint configuration."""
    tool_input = json.load(sys.stdin).get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    path = Path(file_path.replace("\\", "/"))
    root = checkout_of(path) if file_path else None
    if root is None:
        return 0
    rel = PurePosixPath(path.relative_to(root).as_posix())
    what = lint_change(rel, path, tool_input)
    if what:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "ask",
                        "permissionDecisionReason": REASON.format(what=what),
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
