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


class MissingMandatoryTargetValidationPlugin(ResourceValidationPlugin):
    """A resource-scoped validation plugin validating that every origin defines at least
    one target resource for relations that are mandatory at the target end.

    This only applies to schemapack classes with relations that are mandatory at the
    target end.
    """

    @staticmethod
    def does_apply(*, class_: ClassDefinition) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given schemapack.

        Returns: True if this plugin is relevant for the given class definition.
        """
        return any(relation.mandatory.target for relation in class_.relations.values())

    def __init__(self, *, class_: ClassDefinition):
        """This plugin is configured with one specific class definition of a schemapack."""
        self._relations_of_interest = {
            relation_name
            for relation_name, relation in class_.relations.items()
            if relation.mandatory.target
        }

    def validate(
        self, *, resource: Resource, resource_id: ResourceId, datapack: DataPack
    ):
        """Validates a specific resource of the defined class. The entire datapack is
        provided for resolving relations to resources of other classes.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        relations_with_missing_targets: set[str] = set()

        for relation_name in self._relations_of_interest:
            try:
                target_resource_ids = resource.relations[relation_name].targetResources
            except KeyError:
                # This is an error but needs to be handled by another validation plugin:
                continue

            if not target_resource_ids:
                relations_with_missing_targets.add(relation_name)

        if relations_with_missing_targets:
            raise ValidationPluginError(
                type_="MissingMandatoryTargetError",
                message=(
                    "No targets were defined for the following mandatory relations: "
                    + ", ".join(relations_with_missing_targets)
                ),
                details={
                    "relations_with_missing_targets": relations_with_missing_targets,
                },
            )
