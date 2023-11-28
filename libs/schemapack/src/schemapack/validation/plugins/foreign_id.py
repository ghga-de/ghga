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

from schemapack.exceptions import ValidationPluginError
from schemapack.spec.datapack import DataPack, Resource, ResourceId
from schemapack.spec.schemapack import ClassDefinition
from schemapack.validation.base import ResourceValidationPlugin


class ForeignIdValidationPlugin(ResourceValidationPlugin):
    """A resource-scoped validation plugin validating that all relations of a given
    resource point to existing foreign resources.
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
            schemapack.exceptions.DataValidationError: If validation fails.
        """
        non_found_foreign_ids: dict[str, str] = {}  # foreign_id -> relation_name
        for relation_name, relation in self._relations.items():
            foreign_ids = resource.relations.get(relation_name, [])

            if not isinstance(foreign_ids, list):
                foreign_ids = [foreign_ids]

            for foreign_id in foreign_ids:
                if foreign_id not in datapack.resources.get(relation.to, {}):
                    non_found_foreign_ids[foreign_id] = relation_name

        if non_found_foreign_ids:
            raise ValidationPluginError(
                type_="ForeignIdNotFoundError",
                message=(
                    "Did not find a foreign resource for the following ID(s) (relation"
                    + " names): "
                    + ", ".join(
                        f"'{foreign_id}' ('{relation_name}')"
                        for foreign_id, relation_name in non_found_foreign_ids.items()
                    )
                ),
                details={
                    "non_found_foreign_ids": non_found_foreign_ids.keys(),
                    "corresponding_relation_names": non_found_foreign_ids.values(),
                },
            )
