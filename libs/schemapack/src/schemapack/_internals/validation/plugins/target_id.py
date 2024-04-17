# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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


class TargetIdValidationPlugin(ResourceValidationPlugin):
    """A resource-scoped validation plugin validating that all relations of a given
    resource point to existing target resources.
    This plugin only applies if the schemapack class defines any relations.
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
        self._relations = class_.relations

    def validate(
        self, *, resource: Resource, resource_id: ResourceId, datapack: DataPack
    ):
        """Validates a specific resource of the defined class. The entire datapack is
        provided for resolving relations to resources of other classes.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        non_found_target_ids: dict[str, str] = {}  # target_id -> relation_name
        for relation_name, relation in self._relations.items():
            target_ids = resource.get_target_id_set(relation_name, do_not_raise=True)

            for target_id in target_ids:
                if target_id not in datapack.resources.get(relation.targetClass, set()):
                    non_found_target_ids[target_id] = relation_name

        if non_found_target_ids:
            raise ValidationPluginError(
                type_="TargetIdNotFoundError",
                message=(
                    "Did not find a target resource for the following ID(s) (relation"
                    + " names): "
                    + ", ".join(
                        f"'{target_id}' ('{relation_name}')"
                        for target_id, relation_name in non_found_target_ids.items()
                    )
                ),
                details={
                    "non_found_target_ids": non_found_target_ids.keys(),
                    "corresponding_relation_names": non_found_target_ids.values(),
                },
            )
