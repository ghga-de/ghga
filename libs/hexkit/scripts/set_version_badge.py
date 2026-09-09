#!/usr/bin/env python3

# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Quarto pre-render hook: show this package's own version in the navbar badge.

great-docs fills the badge from ``_package_meta.json``, which it derives from the
latest GitHub Release of the repository named by ``repo:``. In a monorepo that is
whichever component was tagged last, not this package. This hook rewrites the file
from the version declared in the package's own ``pyproject.toml`` — the version the
PyPI lane releases from.

``published_at`` is omitted: a declared version is often not tagged yet, so any date
would be a guess, and the badge then shows no tooltip.

Registered via ``pre_render:`` in ``great-docs.yml``. Quarto runs it with the build
project directory as CWD and also exposes ``QUARTO_PROJECT_DIR``.

TODO: Drop this once great-docs can be told the version directly (as of 0.17.0 there
is no config key for it).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import tomllib

META_FILE = "_package_meta.json"


def _project_dir() -> Path:
    env = os.environ.get("QUARTO_PROJECT_DIR")
    if env:
        return Path(env)
    # Script is copied to <project>/scripts/, so the project dir is its grandparent.
    return Path(__file__).resolve().parent.parent


def main() -> int:
    project_dir = _project_dir()
    # The build directory sits inside the package, so the manifest is one level up.
    pyproject = project_dir.parent / "pyproject.toml"
    if not pyproject.is_file():
        print(f"[set_version_badge] no pyproject.toml at {pyproject}; skipping")
        return 0

    version = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    (project_dir / META_FILE).write_text(
        json.dumps({"version": version}), encoding="utf-8"
    )
    print(f"[set_version_badge] set the navbar badge to v{version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
