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

"""Test schema comparison functionality."""

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import pytest
from arcticfreeze import FrozenDict

from schemapack import (
    is_equal_schemapack,
    is_equivalent_schemapack,
    load_schemapack,
)
from schemapack._internals.compare import (
    compare_class_relations_semantically,
    compare_relations_semantically,
)
from schemapack._internals.exceptions import (
    InequivalentContentSchemas,
    InequivalentSchemapacks,
)
from schemapack._internals.spec.schemapack import (
    ClassRelation,
    MandatoryRelationSpec,
    MultipleRelationSpec,
)
from tests.fixtures.examples import (
    COMPARISON_SCHEMAPACK_PATHS,
    REPRESENTATIVE_SCHEMAPACK_PATHS,
    SCHEMAPACK_PAIRED_COMPARISON_PATHS,
)

# Expected comparison results for each test case
# True indicates schemapacks should be considered equal
EXPECTED_RESULTS = {
    "equal_schemas_optional_untyped_property": True,
    "equal_schemas_with_relations": True,
    "unequal_schemas_different_classes": False,
    "unequal_schemas_different_relation_spec": False,
    "unequal_schemas_different_content": False,
}

EXPECTED_EXCEPTIONS = {
    "equal_schemas_optional_untyped_property": None,
    "equal_schemas_with_relations": None,
    "unequal_schemas_different_classes": InequivalentSchemapacks,
    "unequal_schemas_different_relation_spec": InequivalentContentSchemas,
    "unequal_schemas_different_content": InequivalentContentSchemas,
}


@dataclass
class _Relation:
    """Defines constraints and cardinality rules for a test relation."""

    target_class: str
    mandatory_origin: bool = True
    mandatory_target: bool = True
    multiple_origin: bool = True
    multiple_target: bool = True

    def _make_class_relation(self) -> ClassRelation:
        return ClassRelation(
            targetClass=self.target_class,
            mandatory=MandatoryRelationSpec(
                origin=self.mandatory_origin, target=self.mandatory_target
            ),
            multiple=MultipleRelationSpec(
                origin=self.multiple_origin, target=self.multiple_target
            ),
        )


def _relation(*relations: tuple[str, _Relation]) -> FrozenDict:
    """Create one or more ClassRelation entries."""
    return FrozenDict({name: rel._make_class_relation() for name, rel in relations})


@pytest.mark.parametrize(
    "relations1, relations2",
    [
        pytest.param(
            FrozenDict(),
            _relation(("a", _Relation(target_class="B"))),
            id="one_empty",
        ),
        pytest.param(
            _relation(("a", _Relation(target_class="B"))),
            _relation(("b", _Relation(target_class="B"))),
            id="different_keys",
        ),
        pytest.param(
            _relation(("a", _Relation(target_class="B"))),
            _relation(("a", _Relation(target_class="C"))),
            id="different_target_class",
        ),
        pytest.param(
            _relation(
                ("a", _Relation(target_class="B", mandatory_origin=True)),
                ("c", _Relation(target_class="C")),
            ),
            _relation(("a", _Relation(target_class="B", mandatory_origin=True))),
            id="different_relation_counts",
        ),
    ],
)
def test_compare_relations_unhappy(relations1: FrozenDict, relations2: FrozenDict):
    """Test semantic equality of relation mappings for various cases."""
    assert not compare_relations_semantically(relations1, relations2)


def test_compare_empty_relations():
    """Test that empty relations are considered semantically equal."""
    assert compare_relations_semantically(FrozenDict(), FrozenDict())


def test_compare_class_relations_happy():
    """Test that identical ClassRelation objects are equal."""
    relation1 = _Relation(target_class="B")._make_class_relation()
    relation2 = _Relation(target_class="B")._make_class_relation()
    assert compare_class_relations_semantically(relation1, relation2)


@pytest.mark.parametrize(
    "relation1, relation2",
    [
        pytest.param(
            _Relation(target_class="B")._make_class_relation(),
            _Relation(target_class="C")._make_class_relation(),
            id="different_target_class",
        ),
        pytest.param(
            _Relation(target_class="B", mandatory_origin=True)._make_class_relation(),
            _Relation(target_class="B", mandatory_origin=False)._make_class_relation(),
            id="different_mandatory_origin",
        ),
        pytest.param(
            _Relation(target_class="B", mandatory_target=True)._make_class_relation(),
            _Relation(target_class="B", mandatory_target=False)._make_class_relation(),
            id="different_mandatory_target",
        ),
        pytest.param(
            _Relation(target_class="B", multiple_origin=True)._make_class_relation(),
            _Relation(target_class="B", multiple_origin=False)._make_class_relation(),
            id="different_multiple_origin",
        ),
        pytest.param(
            _Relation(target_class="B", multiple_target=True)._make_class_relation(),
            _Relation(target_class="B", multiple_target=False)._make_class_relation(),
            id="different_multiple_target",
        ),
    ],
)
def test_compare_class_relations_unhappy(
    relation1: ClassRelation, relation2: ClassRelation
):
    """Test semantic equality of ClassRelation objects."""
    assert not compare_class_relations_semantically(relation1, relation2)


@pytest.mark.parametrize(
    "path", COMPARISON_SCHEMAPACK_PATHS.values(), ids=COMPARISON_SCHEMAPACK_PATHS
)
def test_equivalence_reflexivity(path: Path):
    """
    Verify reflexivity of schemapack equivalence.

    A schemapack must be equivalent to itself.
    """
    schema = load_schemapack(path)
    assert is_equivalent_schemapack(schema, schema)


@pytest.mark.parametrize(
    "name, path1, path2",
    SCHEMAPACK_PAIRED_COMPARISON_PATHS,
    ids=[
        f"{name}: {path1.name} vs {path2.name}"
        for name, path1, path2 in SCHEMAPACK_PAIRED_COMPARISON_PATHS
    ],
)
def test_equivalence_symmetry_and_transitivity(name: str, path1: Path, path2: Path):
    """
    Verify symmetry of schemapack equivalence on known equivalent pairs.

    For each known equivalent pair (A, B), equivalence must hold in both
    directions: A ≡ B and B ≡ A.

    Transitivity is covered implicitly by the completeness of the equivalent
    pair set used for parametrization.
    """
    schema1 = load_schemapack(path1)
    schema2 = load_schemapack(path2)
    assert is_equivalent_schemapack(schema1, schema2)
    assert is_equivalent_schemapack(schema2, schema1)


@pytest.mark.parametrize(
    "path1, path2",
    list(combinations(REPRESENTATIVE_SCHEMAPACK_PATHS.values(), 2)),
    ids=[
        f"{path1.parent.name}.{path1.stem.split('.')[0]} vs {path2.parent.name}.{path2.stem.split('.')[0]}"
        for path1, path2 in combinations(REPRESENTATIVE_SCHEMAPACK_PATHS.values(), 2)
    ],
)
def test_inequivalence(path1: Path, path2: Path):
    """
    Verify inequivalence across representative schemapacks from different test cases.

    Any two schemapacks chosen from different representative scenarios must
    not be considered equivalent.
    """
    schema1 = load_schemapack(path1)
    schema2 = load_schemapack(path2)
    assert not is_equivalent_schemapack(schema1, schema2)


def test_equal_schemapack_with_identical_file_loaded_twice():
    """Test that the same file loaded twice produces equal objects."""
    path = COMPARISON_SCHEMAPACK_PATHS["ghga_ingress.ingress"]

    schema1 = load_schemapack(path)
    schema2 = load_schemapack(path)

    assert is_equal_schemapack(schema1, schema2)


def test_structurally_different_schemapacks():
    """Testcase where semantically equivalent schemapacks are not structurally equal."""
    path1 = COMPARISON_SCHEMAPACK_PATHS["all_mandatory.some_descriptions"]
    path2 = COMPARISON_SCHEMAPACK_PATHS["all_mandatory.no_descriptions"]

    schema1 = load_schemapack(path1)
    schema2 = load_schemapack(path2)

    assert not is_equal_schemapack(schema1, schema2)
