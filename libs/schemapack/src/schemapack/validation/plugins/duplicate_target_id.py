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

from schemapack.exceptions import ValidationPluginError
from schemapack.spec.datapack import DataPack, Resource, ResourceId
from schemapack.spec.schemapack import ClassDefinition
from schemapack.validation.base import ResourceValidationPlugin


class DuplicateTargetIdValidationPlugin(ResourceValidationPlugin):
    """A resource-scoped validation plugin validating that all target id for *_to_many
    a relation of a given resource are unique.
    This plugin only applies if the schemapack class has any *_to_many relations.
    """

    @staticmethod
    def does_apply(*, class_: ClassDefinition) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given schemapack.

        Returns: True if this plugin is relevant for the given class definition.
        """
        return any(relation.multiple.target for relation in class_.relations.values())

    def __init__(self, *, class_: ClassDefinition):
        """This plugin is configured with one specific class definition of a schemapack."""
        self._relations_of_interest = [
            name
            for name, relation in class_.relations.items()
            if relation.multiple.target
        ]

    def validate(
        self, *, resource: Resource, resource_id: ResourceId, datapack: DataPack
    ):
        """Validates a specific resource of the defined class. The entire datapack is
        provided for resolving relations to resources of other classes.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        # Contains all duplicate target ids (values) per relation (keys) if any
        # overlaps are found for that relation:
        duplicate_ids_by_relation: dict[str, list[str]] = {}

        for relation_name in self._relations_of_interest:
            target_ids = resource.relations.get(relation_name, [])

            if not isinstance(target_ids, list):
                # This is an error, however, it needs to be handled by a different
                # validation plugin
                continue

            duplicate_target_ids = [k for k, v in Counter(target_ids).items() if v > 1]
            if duplicate_target_ids:
                duplicate_ids_by_relation[relation_name] = duplicate_target_ids

        if duplicate_ids_by_relation:
            raise ValidationPluginError(
                type_="DuplicateTargetIdError",
                message=(
                    "Found duplicate target ids for the following relation(s): "
                    + ", ".join(duplicate_ids_by_relation)
                ),
                details={"duplicate_ids_by_relation": duplicate_ids_by_relation},
            )
