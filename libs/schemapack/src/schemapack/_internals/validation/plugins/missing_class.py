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


class MissingClassSlotValidationPlugin(GlobalValidationPlugin):
    """A global-scoped validation plugin validating that a datapack has a slot for
    each class defined in the provided schemapack.
    """

    @staticmethod
    def does_apply(*, schemapack: SchemaPack) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given schemapack.

        Returns: True if this plugin is relevant for the given class definition.
        """
        return True

    def __init__(self, *, schemapack: SchemaPack):
        """This plugin is configured with the entire schemapack."""
        self._classes = schemapack.classes.keys()

    def validate(self, *, datapack: DataPack):
        """Validate the entire datapack.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        missing_classes = [
            class_ for class_ in self._classes if class_ not in datapack.resources
        ]

        if missing_classes:
            raise ValidationPluginError(
                type_="MissingClassSlotError",
                message=("Missing slot(s) for class(es):" + ", ".join(missing_classes)),
                details={
                    "missing_classes": missing_classes,
                },
            )
