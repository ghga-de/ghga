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


class ExpectedRootValidationPlugin(GlobalValidationPlugin):
    """A global-scoped validation plugin validating that a datapack has a root resource.
    This plugin is only relevant if the schemapack has a root class defined.
    """

    @staticmethod
    def does_apply(*, schemapack: SchemaPack) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given schemapack.

        Returns: True if this plugin is relevant for the given class definition.
        """
        return bool(schemapack.rootClass)

    def __init__(self, *, schemapack: SchemaPack):
        """This plugin is configured with the entire schemapack."""
        # there is nothing to do

    def validate(self, *, datapack: DataPack):
        """Validate the entire datapack.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        missing = []
        if not datapack.rootResource:
            missing.append("root resource")
        if not datapack.rootClass:
            missing.append("root class")

        if missing:
            raise ValidationPluginError(
                type_="ExpectedRootDefinitionError",
                message=(
                    "The schemapack has a root class defined but the datapack "
                    f"is missing a {' and '.join(missing)}."
                ),
            )
