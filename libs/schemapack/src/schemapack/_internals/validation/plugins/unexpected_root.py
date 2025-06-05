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

from schemapack._internals.validation.base import GlobalValidationPlugin
from schemapack.exceptions import ValidationPluginError
from schemapack.spec.datapack import DataPack
from schemapack.spec.schemapack import SchemaPack


class UnexpectedRootValidationPlugin(GlobalValidationPlugin):
    """A global-scoped validation plugin validating that a datapack has no root resource
    and root class defined.
    This plugin is only relevant if the schemapack has no root class defined.
    """

    @staticmethod
    def does_apply(*, schemapack: SchemaPack) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given schemapack.

        Returns: True if this plugin is relevant for the given class definition.
        """
        return not bool(schemapack.rootClass)

    def __init__(self, *, schemapack: SchemaPack):
        """This plugin is configured with the entire schemapack."""
        # there is nothing to do

    def validate(self, *, datapack: DataPack):
        """Validate the entire datapack.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        defined = []
        if datapack.rootResource:
            defined.append("root resource")
        if datapack.rootClass:
            defined.append("root class")

        if defined:
            raise ValidationPluginError(
                type_="UnexpectedRootDefinitionError",
                message=(
                    "The schemapack has no root class defined but the datapack "
                    f"specifies a {' and '.join(defined)}."
                ),
            )
