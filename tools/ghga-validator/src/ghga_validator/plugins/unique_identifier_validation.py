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

"""Plugin for validating the identifier uniqueness"""

from ghga_validator.core.models import ValidationMessage, ValidationResult
from ghga_validator.linkml.object_iterator import ObjectIterator
from ghga_validator.plugins.base_plugin import ValidationPlugin
from ghga_validator.utils import path_as_string


class UniqueIdentifierValidationPlugin(ValidationPlugin):
    """
    Plugin to check whether the fields defined as identifier/unique key
    are unique for a class.
    """

    NAME = "UniqueIdentifierValidationPlugin"

    def validate(self, data: dict, target_class: str) -> ValidationResult:
        """
        Perform validation on an object.

        Args:
            data: The JSON object to validate
            target_class: class name for root class

        Returns:
            ValidationResult: A validation result that describes the outcome of validation

        """
        messages = self.validate_unique_fields(data, target_class)
        valid = len(messages) == 0

        result = ValidationResult(
            plugin_name=self.NAME, valid=valid, validation_messages=messages
        )
        return result

    def validate_unique_fields(
        self,
        object_to_validate: dict,
        target_class: str,
    ) -> list[ValidationMessage]:
        """
        Validate non inlined reference fields in a JSON object

        Args:
            object_to_validate: input JSON object
            target_class: parent class in the schema

        Returns:
            SlotDefinition: class definition

        """
        messages = []

        seen_ids: dict[tuple, list] = {}
        for class_name, identifier, data, path in ObjectIterator(
            self.schema, object_to_validate, target_class
        ):
            id_slot = self.schema.get_identifier_slot(class_name)
            id_slot_name = id_slot.name if id_slot is not None else "UNKNOWN"
            if (class_name, identifier) in seen_ids:
                previous_path = seen_ids[class_name, identifier]
                message = ValidationMessage(
                    message="Duplicate value for identifier, "
                    + f"same value used at {path_as_string(previous_path)}.",
                    field=f"{path_as_string(path)}.{id_slot_name}",
                    value=data[id_slot_name],
                )
                messages.append(message)
            else:
                seen_ids[class_name, identifier] = [*path, id_slot_name]
        return messages
