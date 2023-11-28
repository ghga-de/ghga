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

"""Tests the models module."""


from schemapack.load import load_schemapack
from tests.fixtures.examples import VALID_SCHEMAPACK_PATHS


def test_schemapack_is_hashable():
    """Test that instances of SchemaPack are hashable."""
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS["rooted"])
    _ = hash(schemapack)


def test_hashing_of_equivalent_schemapacks():
    """Test that equivalent schemapack (content schemas embedded or not) have the same
    hash.
    """
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS["rooted"])
    schemapack_condensed = load_schemapack(VALID_SCHEMAPACK_PATHS["rooted_condensed"])

    assert hash(schemapack) == hash(schemapack_condensed)


def test_hashing_of_different_schemapacks():
    """Test that different SchemaPack instances have different hashes."""
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS["rooted"])
    schemapack_modified = schemapack.model_copy(update={"root": None})

    assert hash(schemapack) != hash(schemapack_modified)


def test_comparison_of_equivalent_schemapacks():
    """Test that equivalent schemapack (content schemas embedded or not) definitions
    are considered equal.
    """
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS["rooted"])
    schemapack_condensed = load_schemapack(VALID_SCHEMAPACK_PATHS["rooted_condensed"])

    assert schemapack == schemapack_condensed


def test_comparison_of_different_schemapacks():
    """Test that different schemapack definitions fail equality checks."""
    schemapack = load_schemapack(VALID_SCHEMAPACK_PATHS["rooted"])
    schemapack_modified = schemapack.model_copy(update={"root": None})

    assert schemapack != schemapack_modified
