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

"""Compare two schema definitions for semantic equality."""

from arcticfreeze import FrozenDict
from jsonsubschema import isEquivalent

from schemapack._internals.exceptions import (
    ComparisonError,
    InequivalentContentSchemas,
    InequivalentSchemapacks,
)
from schemapack._internals.spec.custom_types import ContentSchema, RelationPropertyName
from schemapack._internals.spec.schemapack import ClassDefinition, ClassRelation
from schemapack._internals.utils import thaw
from schemapack.spec.schemapack import SchemaPack

__all__ = [
    "assert_equal_schemapack",
    "assert_equivalent_schemapack",
    "is_equal_schemapack",
    "is_equivalent_schemapack",
]


def compare_relations_semantically(
    relations1: FrozenDict[RelationPropertyName, ClassRelation],
    relations2: FrozenDict[RelationPropertyName, ClassRelation],
) -> bool:
    """Compare two relations for semantic equality."""
    if not relations1 and not relations2:
        return True

    if relations1.keys() != relations2.keys():
        return False

    for key in relations1:
        if not compare_class_relations_semantically(relations1[key], relations2[key]):
            return False
    return True


def compare_class_relations_semantically(
    relation1: ClassRelation,
    relation2: ClassRelation,
) -> bool:
    """Compare two ClassRelation objects to determine whether they are equivalent.
    `description` attribute is omitted from the comparison.
    """
    return (
        relation1.targetClass == relation2.targetClass
        and relation1.mandatory == relation2.mandatory
        and relation1.multiple == relation2.multiple
    )


def compare_content_semantically(
    schema1: ContentSchema, schema2: ContentSchema
) -> bool:
    """Compare two content schemas to determine whether they are equivalent."""
    try:
        return isEquivalent(thaw(schema1), thaw(schema2))
    except Exception as exp:
        raise ComparisonError("An error happened while comparing the schemas.") from exp


def compare_class_definitions_semantically(
    class_def1: ClassDefinition,
    class_def2: ClassDefinition,
) -> bool:
    """Compare two ClassDefinition objects to determine whether they are equivalent."""
    return (
        class_def1.id.propertyName == class_def2.id.propertyName
        and compare_relations_semantically(class_def1.relations, class_def2.relations)
        and compare_content_semantically(class_def1.content, class_def2.content)
    )


def assert_equivalent_schemapack(
    schemapack1: SchemaPack, schemapack2: SchemaPack
) -> None:
    """Assert that two schemapacks are equivalent."""
    if schemapack1.rootClass != schemapack2.rootClass:
        raise InequivalentSchemapacks(
            f"Root class mismatch between schemapacks: "
            f"{schemapack1.rootClass} != {schemapack2.rootClass}"
        )

    # Compare class names as sets (order doesn't matter, only membership).
    if schemapack1.classes.keys() != schemapack2.classes.keys():
        difference = schemapack1.classes.keys() ^ schemapack2.classes.keys()
        raise InequivalentSchemapacks(
            f"Class set mismatch between schemapacks for classes: {difference}."
        )

    for class_name in schemapack1.classes:
        if not compare_class_definitions_semantically(
            schemapack1.classes[class_name],
            schemapack2.classes[class_name],
        ):
            raise InequivalentContentSchemas(
                f"Class definition mismatch for '{class_name}'"
            )


def is_equivalent_schemapack(schemapack1: SchemaPack, schemapack2: SchemaPack) -> bool:
    """Check if two schemapacks are equivalent."""
    try:
        assert_equivalent_schemapack(schemapack1, schemapack2)
        return True
    except (InequivalentSchemapacks, InequivalentContentSchemas):
        return False


def assert_equal_schemapack(schemapack1: SchemaPack, schemapack2: SchemaPack) -> None:
    """Assert structural equality of two schemapacks.

    The schemapacks are considered equal if their model instances compare equal
    via '=='. If they are not equal, an 'InequivalentSchemapacks' exception
    is raised.
    """
    if schemapack1 != schemapack2:
        raise InequivalentSchemapacks("Schemapacks are not equal.")


def is_equal_schemapack(schemapack1: SchemaPack, schemapack2: SchemaPack) -> bool:
    """Check structural equality of two schemapacks.

    Returns 'True' if the schemapacks are structurally equal according to
    'assert_equal_schemapack', otherwise returns 'False'.
    """
    try:
        assert_equal_schemapack(schemapack1, schemapack2)
    except InequivalentSchemapacks:
        return False
    return True
