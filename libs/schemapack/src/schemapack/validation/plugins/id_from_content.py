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


class IdFromContentValidationPlugin(ResourceValidationPlugin):
    """A resource-scoped validation plugin validating that the provided resource ID
    matches the corresponding property in the content.
    This only applies of the 'from_content' field is used in the class definition in the
    schemapack to define the resource ID.
    """

    @staticmethod
    def does_apply(*, class_: ClassDefinition) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given schemapack.

        Returns: True if this plugin is relevant for the given class definition.
        """
        return bool(class_.id.from_content)

    def __init__(self, *, class_: ClassDefinition):
        """This plugin is configured with one specific class definition of a schemapack."""
        self._id_property = class_.id.from_content

    def validate(
        self, *, resource: Resource, resource_id: ResourceId, datapack: DataPack
    ):
        """Validates a specific resource of the defined class. The entire datapack is
        provided for resolving relations to resources of other classes.

        Raises:
            schemapack.exceptions.DataValidationError: If validation fails.
        """
        if resource_id != (expected_id := resource.content.get(self._id_property)):
            raise ValidationPluginError(
                type_="IdContentMismatchError",
                message=(
                    "The ID did not match the corresponding content property: "
                    + f"got '{resource_id}' but expected '{expected_id}'"
                ),
                details={
                    "resource_id": resource_id,
                    "expected_id": expected_id,
                },
            )
