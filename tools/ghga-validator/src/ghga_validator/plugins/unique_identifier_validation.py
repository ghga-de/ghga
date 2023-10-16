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

"""Plugin for LinkML JSON Validator used for validating the non inline references"""

from linkml_runtime.utils.schemaview import SchemaView
from linkml_validator.models import SeverityEnum, ValidationMessage, ValidationResult
from linkml_validator.plugins.base import BasePlugin

from ghga_validator.linkml.object_iterator import ObjectIterator
from ghga_validator.utils import path_as_string


class UniqueIdentifierValidationPlugin(BasePlugin):
    """
    Plugin to check whether the fields defined as identifier/unique key
    are unique for a class.

    Args:
        schema: Path or URL to schema YAML
        kwargs: Additional arguments that are used to instantiate the plugin

    """

    NAME = "UniqueIdentifierValidationPlugin"

    def __init__(self, schema: str) -> None:
        super().__init__(schema)
        self.schemaview = SchemaView(schema)

    def process(self, obj: dict, **kwargs) -> ValidationResult:
        """
        Perform validation on an object.

        Args:
            obj: The object to validate
            kwargs: Additional arguments that are used for processing

        Returns:
            ValidationResult: A validation result that describes the outcome of validation

        """
        target_class = kwargs["target_class"]

        messages = self.validate_unique_fields(obj, target_class)
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
            self.schemaview, object_to_validate, target_class
        ):
            id_slot = self.schemaview.get_identifier_slot(class_name)
            id_slot_name = id_slot.name if id_slot is not None else "UNKNOWN"
            if (class_name, identifier) in seen_ids:
                previous_path = seen_ids[class_name, identifier]
                message = ValidationMessage(
                    severity=SeverityEnum.error,
                    message="Duplicate value for identifier, "
                    + f"same value used at {path_as_string(previous_path)}.",
                    field=f"{path_as_string(path)}.{id_slot_name}",
                    value=data[id_slot_name],
                )
                messages.append(message)
            else:
                seen_ids[class_name, identifier] = [*path, id_slot_name]
        return messages
