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

"""Test schema comparison functionality."""

from dataclasses import dataclass
from pathlib import Path

import pytest
from arcticfreeze import FrozenDict

from schemapack import load_schemapack
from schemapack._internals.compare import (
    assert_equivalent_schemapack,
    compare_class_relations,
    compare_relations,
    is_equivalent_schemapack,
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
from tests.fixtures.examples import COMPARISON_SCHEMAPACK_PATHS

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


def _make_class_relation(relation: _Relation) -> ClassRelation:
    return ClassRelation(
        targetClass=relation.target_class,
        mandatory=MandatoryRelationSpec(
            origin=relation.mandatory_origin, target=relation.mandatory_target
        ),
        multiple=MultipleRelationSpec(
            origin=relation.multiple_origin, target=relation.multiple_target
        ),
    )


def _make_relation(*relations: tuple[str, _Relation]) -> FrozenDict:
    """Create one or more ClassRelation entries."""
    return FrozenDict({name: _make_class_relation(rel) for name, rel in relations})


@pytest.mark.parametrize(
    "relations1, relations2, expected",
    [
        pytest.param(
            FrozenDict(),
            FrozenDict(),
            True,
            id="both_empty",
        ),
        pytest.param(
            FrozenDict(),
            _make_relation(("a", _Relation(target_class="B"))),
            False,
            id="one_empty",
        ),
        pytest.param(
            _make_relation(("a", _Relation(target_class="B"))),
            _make_relation(("b", _Relation(target_class="B"))),
            False,
            id="different_keys",
        ),
        pytest.param(
            _make_relation(("a", _Relation(target_class="B"))),
            _make_relation(("a", _Relation(target_class="C"))),
            False,
            id="different_target_class",
        ),
        pytest.param(
            _make_relation(
                ("a", _Relation(target_class="B", mandatory_origin=True)),
                ("c", _Relation(target_class="C")),
            ),
            _make_relation(("a", _Relation(target_class="B", mandatory_origin=True))),
            False,
            id="different_relation_counts",
        ),
    ],
)
def test_compare_relations(
    relations1: FrozenDict, relations2: FrozenDict, expected: bool
):
    """Test semantic equality of relation mappings for various cases."""
    assert compare_relations(relations1, relations2) is expected


def test_compare_class_relations_happy():
    """Test that identical ClassRelation objects are equal."""
    relation1 = _make_class_relation(_Relation(target_class="B"))
    relation2 = _make_class_relation(_Relation(target_class="B"))
    assert compare_class_relations(relation1, relation2)


@pytest.mark.parametrize(
    "relation1, relation2",
    [
        pytest.param(
            _make_class_relation(_Relation(target_class="B")),
            _make_class_relation(_Relation(target_class="C")),
            id="different_target_class",
        ),
        pytest.param(
            _make_class_relation(_Relation(target_class="B", mandatory_origin=True)),
            _make_class_relation(_Relation(target_class="B", mandatory_origin=False)),
            id="different_mandatory_origin",
        ),
        pytest.param(
            _make_class_relation(_Relation(target_class="B", mandatory_target=True)),
            _make_class_relation(_Relation(target_class="B", mandatory_target=False)),
            id="different_mandatory_target",
        ),
        pytest.param(
            _make_class_relation(_Relation(target_class="B", multiple_origin=True)),
            _make_class_relation(_Relation(target_class="B", multiple_origin=False)),
            id="different_multiple_origin",
        ),
        pytest.param(
            _make_class_relation(_Relation(target_class="B", multiple_target=True)),
            _make_class_relation(_Relation(target_class="B", multiple_target=False)),
            id="different_multiple_target",
        ),
    ],
)
def test_compare_class_relations_unhappy(
    relation1: ClassRelation, relation2: ClassRelation
):
    """Test semantic equality of ClassRelation objects."""
    assert not compare_class_relations(relation1, relation2)


@pytest.mark.parametrize(
    "case_name, schema1_path, schema2_path", COMPARISON_SCHEMAPACK_PATHS
)
def test_assert_equivalent_schemapack(
    case_name: str, schema1_path: Path, schema2_path: Path
):
    """Test that assert_equivalent_schemapack raises the correct exception."""
    schema1 = load_schemapack(schema1_path)
    schema2 = load_schemapack(schema2_path)
    expected_exception = EXPECTED_EXCEPTIONS[case_name]

    if expected_exception is None:
        assert_equivalent_schemapack(schema1, schema2)
    else:
        with pytest.raises(expected_exception):
            assert_equivalent_schemapack(schema1, schema2)


@pytest.mark.parametrize(
    "case_name, schema1_path, schema2_path", COMPARISON_SCHEMAPACK_PATHS
)
def test_is_equivalent_schemapack(
    case_name: str, schema1_path: Path, schema2_path: Path
):
    """Test comparing two schemapacks semantically."""
    schema1 = load_schemapack(schema1_path)
    schema2 = load_schemapack(schema2_path)

    assert is_equivalent_schemapack(schema1, schema2) == EXPECTED_RESULTS[case_name]
