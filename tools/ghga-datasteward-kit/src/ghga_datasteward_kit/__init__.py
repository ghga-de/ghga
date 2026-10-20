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

"""A utils package for GHGA data stewards."""

import re
import subprocess
from importlib.metadata import version
from pathlib import Path

# What a platform-lane member declares in its pyproject.toml (ADR-0046)
PLACEHOLDER = "0.0.0"
FALLBACK = "0.0.0+dev"

# `git describe --abbrev=7 --dirty` output, e.g. ghga/15.3.1-rc.8-71-g44594f5-dirty
DESCRIBE = re.compile(
    r"^ghga/(?P<tag>.+?)(?:-(?P<count>\d+)-g(?P<sha>[0-9a-f]+))?(?P<dirty>-dirty)?$"
)


def checkout_version(described: str | None = None) -> str:
    """Derives the platform version from the checkout this package was run from.

    Stewards run the kit from a clone of a `ghga/` tag, where nothing stamps the
    installed version. A copy of `scripts/platform_version.py`, which this package
    cannot import; docs/releases.md defines the format.

    Args:
        described:
            `git describe` output to convert; None runs git in the package directory.
    """
    if described is None:
        try:
            result = subprocess.run(
                [  # noqa: S607
                    "git",
                    "describe",
                    "--tags",
                    "--match",
                    "ghga/*",
                    "--dirty",
                    "--abbrev=7",
                ],
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return FALLBACK
        if result.returncode:
            return FALLBACK
        described = result.stdout.strip()
    match = DESCRIBE.match(described)
    if not match:
        return FALLBACK
    build = []
    if match["count"]:
        build += ["dev", match["count"], match["sha"]]
    if match["dirty"]:
        build.append("dirty")
    return match["tag"] + ("+" + ".".join(build) if build else "")


__version__ = version(__package__)
if __version__ == PLACEHOLDER:
    __version__ = checkout_version()
