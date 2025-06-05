# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from tests.fixtures.utils import ROOT_DIR

EXAMPLES_DIR = ROOT_DIR / "examples"
SCHEMAPACK_DIR = EXAMPLES_DIR / "schemapack"
VALID_SCHEMAPACK_DIR = SCHEMAPACK_DIR / "valid"
INVALID_SCHEMAPACK_DIR = SCHEMAPACK_DIR / "invalid"
ERD_DIR = EXAMPLES_DIR / "erd"
DATAPACK_DIR = EXAMPLES_DIR / "datapack"
VALID_DATAPACK_DIR = DATAPACK_DIR / "valid"
INVALID_DATAPACK_DIR = DATAPACK_DIR / "invalid"
DENORMALIZED_DEEP_EMBEDDING_DIR = EXAMPLES_DIR / "denormalized" / "deep_embedding"
DENORMALIZED_CUSTOM_EMBEDDING_DIR = EXAMPLES_DIR / "denormalized" / "custom_embedding"

schemapack_suffix = ".schemapack.yaml"
datapack_suffix = ".datapack.yaml"
denomalizated_suffix = ".denormalized.yaml"
erd_suffix = ".mm.txt"


def list_examples_in_dir(dir: Path, *, suffix: str) -> dict[str, Path]:
    """List all example files with the given suffix in the given dir.

    Returns:
        A dict of {example_name: path}.
    """
    examples = {
        path.name.removesuffix(suffix): path
        for path in dir.iterdir()
        if path.name.endswith(suffix)
    }

    return dict(sorted(examples.items()))


def list_examples_in_nested_dir(dir: Path, *, suffix: str) -> dict[str, Path]:
    """List all example files with the given suffix contained in the sub-directories
    inside the provided dictionary.

    Returns:
        A dict of {"subdir.example_name": path}.
    """
    examples = {
        f"{subdir.name}.{example_name}": example
        for subdir in dir.iterdir()
        if not subdir.is_file()
        for example_name, example in list_examples_in_dir(subdir, suffix=suffix).items()
    }

    return dict(sorted(examples.items()))


def list_schemapacks_in_dir(dir: Path) -> dict[str, Path]:
    """List all schemapack files in the given dir.

    Returns:
        A dict of {example_name: path}.
    """
    return list_examples_in_dir(dir, suffix=schemapack_suffix)


VALID_SCHEMAPACK_PATHS = list_schemapacks_in_dir(VALID_SCHEMAPACK_DIR)
INVALID_SCHEMAPACK_PATHS = list_schemapacks_in_dir(INVALID_SCHEMAPACK_DIR)


def list_datapacks_in_dir(dir: Path) -> dict[str, Path]:
    """List all datapack example files per schemapack in the provided dictionary.

    Returns:
        A dict of {"schempack_name.example_name": path}.
    """
    return list_examples_in_nested_dir(dir, suffix=datapack_suffix)


VALID_DATAPACK_PATHS = list_datapacks_in_dir(VALID_DATAPACK_DIR)
INVALID_DATAPACK_PATHS = list_datapacks_in_dir(INVALID_DATAPACK_DIR)


def list_denormalized_in_dir(dir: Path) -> dict[str, Path]:
    """List all denomalizated example files in the given dir.

    Returns:
        A dict of {example_name: path}.
    """
    return list_examples_in_nested_dir(dir, suffix=denomalizated_suffix)


DENORMALIZED_DEEP_EMBEDDING_PATHS = list_denormalized_in_dir(
    DENORMALIZED_DEEP_EMBEDDING_DIR
)
DENORMALIZED_CUSTOM_EMBEDDING_PATHS = list_denormalized_in_dir(
    DENORMALIZED_CUSTOM_EMBEDDING_DIR
)


def list_erds_in_dir(dir: Path) -> dict[str, Path]:
    """List all erd files in the given dir.

    Returns:
        A dict of {example_name: path}.
    """
    return list_examples_in_dir(dir, suffix=erd_suffix)


ERD_PATHS = list_erds_in_dir(ERD_DIR)
