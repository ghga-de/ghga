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
#

"""Example schemapack definitions and associated data."""

from collections import defaultdict
from itertools import combinations
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
EQUIVALENT_SCHEMAPACK_DIR = EXAMPLES_DIR / "equivalent_schemapacks"

schemapack_suffix = ".schemapack.yaml"
datapack_suffix = ".datapack.yaml"
denormalized_suffix = ".denormalized.yaml"
erd_suffix = ".mm.txt"
representative_suffix = ".representative.schemapack.yaml"


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


def list_schemapacks_in_nested_dir(dir: Path) -> dict[str, Path]:
    """List all schemapack files contained in the subdirectories."""
    return list_examples_in_nested_dir(dir, suffix=schemapack_suffix)


COMPARISON_SCHEMAPACK_PATHS = list_schemapacks_in_nested_dir(EQUIVALENT_SCHEMAPACK_DIR)


def list_representative_schemapacks_in_dir(dir: Path) -> dict[str, Path]:
    """List all representative schemapack files in the given directory.

    Representative schemapacks are used as canonical examples for inequivalence tests.
    The returned mapping uses the example name as key and the schemapack file path as value.
    """
    return list_examples_in_nested_dir(dir, suffix=representative_suffix)


REPRESENTATIVE_SCHEMAPACK_PATHS = list_representative_schemapacks_in_dir(
    EQUIVALENT_SCHEMAPACK_DIR
)


def group_comparison_schemapacks_by_test_case(
    comparison_schemapack_paths: dict[str, Path],
) -> dict[str, list[Path]]:
    """
    Group comparison schemapack paths by test case identifier.

    The test case identifier is derived from the schemapack name by taking the prefix
    before the first dot.

    Example:
        {
            "all_mandatory": [path1, path2, path3],
            "rooted": [path4, path5],
        }
    """
    by_class: dict[str, list[Path]] = defaultdict(list)

    for name, path in comparison_schemapack_paths.items():
        class_name = name.split(".", 1)[0]
        by_class[class_name].append(path)
    return by_class


def list_schemapack_comparison_pairs(
    comparison_schemapack_paths: dict[str, Path],
) -> list[tuple[str, Path, Path]]:
    """
    Generate all schemapack path pairs that should be compared for equivalence.

    Each returned tuple consists of:
        (test_case_name, schemapack_path_1, schemapack_path_2)

    Raises:
        ValueError:
            If a test case contains fewer than two schemapack examples.
    """
    by_class = group_comparison_schemapacks_by_test_case(comparison_schemapack_paths)

    test_cases: list[tuple[str, Path, Path]] = []

    for class_name, paths in by_class.items():
        if len(paths) < 2:
            raise ValueError(
                f"Expected at least 2 schemapack examples for class '{class_name}'"
                + f" to compare, but found {len(paths)}."
            )
        for path1, path2 in combinations(paths, 2):
            test_cases.append((class_name, path1, path2))
    return test_cases


SCHEMAPACK_PAIRED_COMPARISON_PATHS = list_schemapack_comparison_pairs(
    COMPARISON_SCHEMAPACK_PATHS
)


def list_denormalized_in_dir(dir: Path) -> dict[str, Path]:
    """List all denormalized example files in the given dir.

    Returns:
        A dict of {example_name: path}.
    """
    return list_examples_in_nested_dir(dir, suffix=denormalized_suffix)


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
