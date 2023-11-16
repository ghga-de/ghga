# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
#

"""Example schemapack definitions and associated data."""

from pathlib import Path

from tests.fixtures.utils import BASE_DIR

EXAMPLES_DIR = BASE_DIR / "examples"
SCHEMAPACK_DIR = EXAMPLES_DIR / "schemapack"
VALID_SCHEMAPACK_DIR = SCHEMAPACK_DIR / "valid"
INVALID_SCHEMAPACK_DIR = SCHEMAPACK_DIR / "invalid"

schemapack_suffix = ".schemapack.yaml"


def list_schemapacks_in_dir(dir: Path):
    """List all schemapack files in the given dir and return a dict of name: path."""
    return {
        path.name.removesuffix(schemapack_suffix): path
        for path in dir.iterdir()
        if path.name.endswith(schemapack_suffix)
    }


VALID_SCHEMAPACK_PATHS = list_schemapacks_in_dir(VALID_SCHEMAPACK_DIR)
INVALID_SCHEMAPACK_PATHS = list_schemapacks_in_dir(INVALID_SCHEMAPACK_DIR)
