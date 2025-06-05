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

"""A validation plugin."""

from schemapack._internals.validation.base import ResourceValidationPlugin
from schemapack.exceptions import ValidationPluginError
from schemapack.spec.custom_types import ResourceId
from schemapack.spec.datapack import DataPack, Resource
from schemapack.spec.schemapack import ClassDefinition


class UnknownRelationValidationPlugin(ResourceValidationPlugin):
    """A resource-scoped validation plugin validating that no relation properties
    are present in a resource that don not exist in the schemapack class.
    This only applies to schemapack classes with relations.
    """

    @staticmethod
    def does_apply(*, class_: ClassDefinition) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given schemapack.

        Returns: True if this plugin is relevant for the given class definition.
        """
        return bool(class_.relations)

    def __init__(self, *, class_: ClassDefinition):
        """This plugin is configured with one specific class definition of a schemapack."""
        self._expected_relations = set(class_.relations)

    def validate(
        self, *, resource: Resource, resource_id: ResourceId, datapack: DataPack
    ):
        """Validates a specific resource of the defined class. The entire datapack is
        provided for resolving relations to resources of other classes.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        unknown_relations = {
            relation
            for relation in resource.relations
            if relation not in self._expected_relations
        }

        if unknown_relations:
            raise ValidationPluginError(
                type_="UnknownRelationPropertyError",
                message=(
                    "The following relation propertie(s) is/are unkown: "
                    + ", ".join(unknown_relations)
                ),
                details={
                    "unknown_relations": unknown_relations,
                    "existing_relations": set(resource.relations),
                },
            )
