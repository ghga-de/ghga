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


class UnkownRootResourceValidationPlugin(GlobalValidationPlugin):
    """A global-scoped validation plugin validating that a datapack has a root resource.
    This plugin is only relevant for the schemapack has a root class defined.
    """

    @staticmethod
    def does_apply(*, schemapack: SchemaPack) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given schemapack.

        Returns: True if this plugin is relevant for the given class definition.
        """
        return bool(schemapack.root_class)

    def __init__(self, *, schemapack: SchemaPack):
        """This plugin is configured with the entire schemapack."""
        self._root_class = cast(str, schemapack.root_class)

    def validate(self, *, datapack: DataPack):
        """Validate the entire datapack.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        root_class_resources = datapack.resources.get(self._root_class)

        if not root_class_resources:
            # This is a validation error but needs to be handled elsewhere:
            return

        if not datapack.root_resource:
            # this is a validation error but needs to be handled elsewhere:
            return

        if datapack.root_resource not in root_class_resources:
            raise ValidationPluginError(
                type_="UnkownRootResourceError",
                message=(
                    "The specified root resource with ID '{root_resource}' of class "
                    + " '{root_class}' does not exist."
                ),
                details={
                    "root_resource": datapack.root_resource,
                    "root_class": self._root_class,
                },
            )
