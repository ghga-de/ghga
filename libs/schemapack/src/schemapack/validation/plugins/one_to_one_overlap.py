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
from schemapack.spec.schemapack import ClassDefinition
from schemapack.validation.base import ClassValidationPlugin


class OneToOneOverlapValidationPlugin(ClassValidationPlugin):
    """A class-scoped validation plugin validating that no overlap in one_to_one
    relations exists across resources of a schemapack class.
    This only applies to schemapack classes with one_to_one relations.
    """

    @staticmethod
    def does_apply(*, class_: ClassDefinition) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given class definition.

        Returns: True if this plugin is relevant for the given class definition.
        """
        return any(
            not relation.multiple.origin and not relation.multiple.target
            for relation in class_.relations.values()
        )

    def __init__(self, *, class_: ClassDefinition):
        """This plugin is configured with one specific class definition of a schemapack."""
        self._relations_of_interest = [
            name
            for name, relation in class_.relations.items()
            if not relation.multiple.origin and not relation.multiple.target
        ]

    def validate(
        self, *, class_resources: Mapping[ResourceId, Resource], datapack: DataPack
    ):
        """Validate all resources of a specific class. The entire datapack is provided
        for resolving relations to other classes.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        # Contains all overlapping target ids (values) per relation (keys) if any
        # overlaps are found for that relation:
        overlapping_ids_by_relation: dict[str, list[str]] = {}

        for relation_name in self._relations_of_interest:
            target_ids: list[str] = []

            for resource in class_resources.values():
                try:
                    target_id = resource.relations[relation_name]
                except KeyError:
                    # This is an error, however, it needs to be handled by a different
                    # validation plugin
                    continue

                if isinstance(target_id, list):
                    # This is an error, however, it needs to be handled by a different
                    # validation plugin
                    continue

                if not target_id:
                    # This is OK (at least assuming mandatory.target is False)
                    continue

                target_ids.append(target_id)

            duplicate_target_ids = [k for k, v in Counter(target_ids).items() if v > 1]

            if duplicate_target_ids:
                overlapping_ids_by_relation[relation_name] = duplicate_target_ids

        if overlapping_ids_by_relation:
            raise ValidationPluginError(
                type_="CardinalityOverlapError",
                message=(
                    "Found overlapping target IDs for the following one_to_one"
                    + " relations:"
                    + ", ".join(overlapping_ids_by_relation.keys())
                ),
                details={"overlapping_ids_by_relation": overlapping_ids_by_relation},
            )
