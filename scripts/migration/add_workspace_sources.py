#!/usr/bin/env python3
"""Wire internal dependencies to the uv workspace (Phase 3 harmonisation).

For every workspace member, find dependencies that resolve to *other workspace members*
(the internal libs/tools) and add `[tool.uv.sources] <name> = { workspace = true }` so they
are consumed from source — the single-`uv.lock`, always-integrated model (ADR-0002).

Version specifiers in `[project.dependencies]` are left untouched here; a follow-up step
relaxes only the specifiers uv reports as incompatible with the workspace HEAD version.

Idempotent: skips members that already have a workspace source for the dep. stdlib only.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MEMBER_GLOBS = ("libs/*", "services/*", "tools/*")
NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def norm(name: str) -> str:
    """PEP 503 normalisation (so ghga_service_commons == ghga-service-commons)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def member_dirs() -> list[Path]:
    out: list[Path] = []
    for glob in MEMBER_GLOBS:
        out += [p for p in sorted(REPO.glob(glob)) if (p / "pyproject.toml").is_file()]
    return out


def dep_names(data: dict) -> set[str]:
    """All declared dependency base names (main + optional-dependencies)."""
    deps: list[str] = list(data.get("project", {}).get("dependencies", []))
    for group in data.get("project", {}).get("optional-dependencies", {}).values():
        deps += group
    names: set[str] = set()
    for spec in deps:
        m = NAME_RE.match(spec)
        if m:
            names.add(norm(m.group(1)))
    return names


def main() -> int:
    members = member_dirs()
    name_to_dir = {}
    for d in members:
        data = tomllib.loads((d / "pyproject.toml").read_text())
        name_to_dir[norm(data["project"]["name"])] = d
    workspace_names = set(name_to_dir)

    changed = []
    for d in members:
        path = d / "pyproject.toml"
        data = tomllib.loads(path.read_text())
        me = norm(data["project"]["name"])
        internal = sorted((dep_names(data) & workspace_names) - {me})
        if not internal:
            continue

        text = path.read_text()
        existing = data.get("tool", {}).get("uv", {}).get("sources", {})
        to_add = [n for n in internal if n not in {norm(k) for k in existing}]
        if not to_add:
            continue

        lines = [f"{n} = {{ workspace = true }}" for n in to_add]
        if "[tool.uv.sources]" in text:
            text = text.replace(
                "[tool.uv.sources]", "[tool.uv.sources]\n" + "\n".join(lines), 1
            )
        else:
            block = "\n[tool.uv.sources]\n" + "\n".join(lines) + "\n"
            text = text.rstrip() + "\n" + block
        path.write_text(text)
        changed.append((d.relative_to(REPO).as_posix(), to_add))

    for member, added in changed:
        print(f"{member}: + {', '.join(added)}")
    print(f"\nUpdated {len(changed)} members.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
