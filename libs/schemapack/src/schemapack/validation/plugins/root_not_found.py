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

from typing import cast

from schemapack.exceptions import ValidationPluginError
from schemapack.spec.datapack import DataPack
from schemapack.spec.schemapack import SchemaPack
from schemapack.validation.base import GlobalValidationPlugin


class RootResourceExistenceValidationPlugin(GlobalValidationPlugin):
    """A resource-scoped validation plugin validating that the root resource specified
    in a datapack exists.
    This plugin only applies to rooted schemapacks.
    """

    @staticmethod
    def does_apply(*, schemapack: SchemaPack) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given schemapack.

        Returns: True if this plugin is relevant for the given class definition.
        """
        return bool(schemapack.root)

    def __init__(self, *, schemapack: SchemaPack):
        """This plugin is configured with the entire schemapack."""
        root_class = schemapack.root
        self._root_class = cast(str, root_class)

    def validate(self, *, datapack: DataPack):
        """Validate the entire datapack.

        Raises:
            schemapack.exceptions.DataValidationError: If validation fails.
        """
        if not datapack.root:
            # This is an error, however, it needs to be handled by a different plugin.
            return

        resources_of_interest = datapack.resources.get(self._root_class, {})
        if datapack.root not in resources_of_interest:
            raise ValidationPluginError(
                type_="RootResourceNotFoundError",
                message=(
                    f"The root resource with ID '{datapack.root}' of class"
                    + f" {self._root_class} does not exist."
                ),
                details={
                    "root_resource": datapack.root,
                    "root_class": self._root_class,
                },
            )
