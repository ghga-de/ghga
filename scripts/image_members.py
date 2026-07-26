#!/usr/bin/env python3
"""Enumerate the workspace members that ship as platform container images.

Single source of truth for the release image matrix
(.github/workflows/release.yaml) and the chart generator
(deploy/src/create_charts.py). Rules per ADR-0014:

- services/*: image by default; opt out via [tool.ghga] release = "pypi"/"none"
  or image = false
- tools/* and libs/*: image only with an explicit [tool.ghga] image marker
- frontend/*: image when a package.json + Dockerfile.dhi pair is present;
  the image name comes from package.json

Convention (ADR-0014): an image member's console script is named exactly like
its distribution, so `package` doubles as the image entrypoint (the shared
Dockerfile's `test -e` guard enforces this at build time).
"""

import json
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _python_members():
    for root, default_image in (("services", True), ("tools", False), ("libs", False)):
        for p in sorted((ROOT / root).iterdir()):
            manifest = p / "pyproject.toml"
            if not manifest.is_file():
                continue
            data = tomllib.loads(manifest.read_text())
            ghga = data.get("tool", {}).get("ghga", {})
            lane = ghga.get("release")
            image = ghga.get(
                "image", default_image if lane not in ("pypi", "none") else False
            )
            if root in ("tools", "libs") and not ghga:
                image = False
            if image:
                project = data["project"]
                yield {
                    "path": str(p.relative_to(ROOT)),
                    "package": project["name"],
                    "kind": "python",
                    "description": project.get("description", ""),
                    "dockerfile": "docker/Dockerfile",
                    "context": ".",
                }


def _frontend_members():
    for p in sorted((ROOT / "frontend").iterdir()):
        manifest = p / "package.json"
        dockerfile = p / "Dockerfile.dhi"
        if not (manifest.is_file() and dockerfile.is_file()):
            continue
        data = json.loads(manifest.read_text())
        yield {
            "path": str(p.relative_to(ROOT)),
            "package": data["name"],
            "kind": "frontend",
            "description": data.get("description", ""),
            "dockerfile": str(dockerfile.relative_to(ROOT)),
            "context": str(p.relative_to(ROOT)),
        }


def image_members() -> list[dict]:
    """All image-building workspace members, python first, then frontend."""
    return [*_python_members(), *_frontend_members()]


if __name__ == "__main__":
    print(json.dumps(image_members()))
