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


class MissingRelationValidationPlugin(ResourceValidationPlugin):
    """A resource-scoped validation plugin validating that all relation properties
    described in the schemapack exist.
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
        self._expected_relations = class_.relations.keys()

    def validate(
        self, *, resource: Resource, resource_id: ResourceId, datapack: DataPack
    ):
        """Validates a specific resource of the defined class. The entire datapack is
        provided for resolving relations to resources of other classes.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        missing_relations = {
            relation
            for relation in self._expected_relations
            if relation not in resource.relations
        }

        if missing_relations:
            raise ValidationPluginError(
                type_="MissingRelationPropertyError",
                message=(
                    "Missing following relation properties: "
                    + ", ".join(missing_relations)
                ),
                details={
                    "missing_relations": missing_relations,
                    "existing_relations": set(resource.relations),
                },
            )
