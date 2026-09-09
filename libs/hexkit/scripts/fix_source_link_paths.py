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

"""Quarto pre-render hook: point great-docs "view source" URLs at the member path.

great-docs resolves an object's source file against the first ``pyproject.toml``
above the build directory. In this workspace that is ``libs/hexkit``, not the
repository root, so the generated GitHub blob URLs read

    /blob/<ref>/src/hexkit/...

and 404 — the file is at ``libs/hexkit/src/hexkit/...``. This hook prepends the
missing member prefix in the generated ``reference/*.qmd`` files, after
great-docs has written them and before Quarto renders them to HTML. It is
idempotent (a URL that already carries the prefix is left untouched).

great-docs' own ``source.path`` override does not solve this: it builds the URL
as ``<source.path>/<basename>``, dropping the package subdirectories, so every
object below the top level would still point at a file that does not exist. See
the note in ``great-docs.yml``.

Registered via ``pre_render:`` in ``great-docs.yml``. Quarto runs it with the
build project directory as CWD and also exposes ``QUARTO_PROJECT_DIR``.

NOTE: ``branch: main`` is pinned in great-docs.yml, so refs never contain a
slash; the ``[^/]+`` ref matcher below is sufficient. Revisit if the source
branch ever becomes a slashed ref (e.g. ``release/1.2``).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# The package's source root, relative to the repository root, and the path
# great-docs actually emits (relative to the member's pyproject.toml).
MEMBER_PREFIX = "libs/hexkit"
EMITTED_PREFIX = "src/hexkit"


def _project_dir() -> Path:
    env = os.environ.get("QUARTO_PROJECT_DIR")
    if env:
        return Path(env)
    # Script is copied to <project>/scripts/, so the project dir is its grandparent.
    return Path(__file__).resolve().parent.parent


def main() -> int:
    reference_dir = _project_dir() / "reference"
    if not reference_dir.is_dir():
        print(f"[fix_source_link_paths] no reference/ dir at {reference_dir}; skipping")
        return 0

    pattern = re.compile(rf"(/blob/[^/]+/){re.escape(EMITTED_PREFIX)}/")
    replacement = rf"\g<1>{MEMBER_PREFIX}/{EMITTED_PREFIX}/"

    changed = 0
    for qmd in sorted(reference_dir.glob("*.qmd")):
        text = qmd.read_text(encoding="utf-8")
        new_text = pattern.sub(replacement, text)
        if new_text != text:
            qmd.write_text(new_text, encoding="utf-8")
            changed += 1

    print(
        f"[fix_source_link_paths] added the {MEMBER_PREFIX}/ prefix "
        f"in {changed} reference file(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
