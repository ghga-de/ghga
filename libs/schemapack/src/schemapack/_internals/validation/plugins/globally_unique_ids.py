# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""A validation plugin."""

from collections import defaultdict

from schemapack._internals.validation.base import GlobalValidationPlugin
from schemapack.exceptions import ValidationPluginError
from schemapack.spec.datapack import DataPack
from schemapack.spec.schemapack import SchemaPack


class GloballyUniqueIdsValidationPlugin(GlobalValidationPlugin):
    """A global-scoped validation plugin ensuring a datapack has globally
    unique IDs for all resources when the schemapack's globallyUniqueIds is set to
    "true".
    """

    @staticmethod
    def does_apply(*, schemapack: SchemaPack) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given schemapack.

        Returns: True if this plugin is relevant for the given class definition.
        """
        return bool(schemapack.globallyUniqueIds)

    def __init__(self, *, schemapack: SchemaPack):
        """This plugin is configured with the entire schemapack."""
        # there is nothing to do

    def validate(self, *, datapack: DataPack):
        """Validate the entire datapack.

        Raises:
            schemapack.exceptions.ValidationPluginError: If validation fails.
        """
        id_to_classes = defaultdict(list)
        for class_name, resources in datapack.resources.items():
            for resource_id in resources:
                id_to_classes[resource_id].append(class_name)

        duplicates = {
            resource_id: classes
            for resource_id, classes in id_to_classes.items()
            if len(classes) > 1
        }
        if duplicates:
            raise ValidationPluginError(
                type_="GloballyUniqueIdsError",
                message="Found resource IDs that are not globally unique across classes.",
                details={"duplicates": duplicates},
            )
