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

"""A validation plugin."""

from collections import Counter
from collections.abc import Mapping

from schemapack.exceptions import ValidationPluginError
from schemapack.spec.datapack import DataPack, Resource, ResourceId
from schemapack.spec.schemapack import Cardinality, ClassDefinition
from schemapack.validation.base import ClassValidationPlugin


class OneToManyOverlapValidationPlugin(ClassValidationPlugin):
    """A resource-scoped validation plugin validating that no overlap in one_to_many
    relations exists across resources of a schemapack class.
    This only applies to schemapack classes with one_to_many relations.
    """

    @staticmethod
    def does_apply(*, class_: ClassDefinition) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given class definition.

        Returns: True if this plugin is relevant for the given class definition.
        """
        return any(
            relation.cardinality == Cardinality.ONE_TO_MANY
            for relation in class_.relations.values()
        )

    def __init__(self, *, class_: ClassDefinition):
        """This plugin is configured with one specific class definition of a schemapack."""
        self._relations_of_interest = [
            name
            for name, relation in class_.relations.items()
            if relation.cardinality == Cardinality.ONE_TO_MANY
        ]

    def validate(
        self, *, class_resources: Mapping[ResourceId, Resource], datapack: DataPack
    ):
        """Validate all resources of a specific class. The entire datapack is provided
        for resolving relations to other classes.

        Raises:
            schemapack.exceptions.DataValidationError: If validation fails.
        """
        # Contains all overlapping foreign ids (values) per relation (keys) if any
        # overlaps are found for that relation:
        overlapping_ids_by_relation: dict[str, list[str]] = {}

        for relation_name in self._relations_of_interest:
            foreign_ids: list[str] = []

            for resource in class_resources.values():
                resource_foreign_ids = resource.relations.get(relation_name, [])

                if not isinstance(resource_foreign_ids, list):
                    # This is an error, however, it needs to be handled by a different
                    # validation plugin
                    continue

                # Deduplicate foreign ids for this resource:
                # (If duplicates exist, this is an error, however, it needs to be
                # handled by a different validation plugin)
                resource_foreign_ids = list(set(resource_foreign_ids))

                foreign_ids.extend(resource_foreign_ids)

            duplicate_foreign_ids = [
                k for k, v in Counter(foreign_ids).items() if v > 1
            ]

            if duplicate_foreign_ids:
                overlapping_ids_by_relation[relation_name] = duplicate_foreign_ids

        if overlapping_ids_by_relation:
            raise ValidationPluginError(
                type_="CardinalityOverlapError",
                message=(
                    "Found overlapping foreign IDs for the following one_to_many"
                    + " relations:"
                    + ", ".join(overlapping_ids_by_relation)
                ),
                details={"overlapping_ids_by_relation": overlapping_ids_by_relation},
            )
