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

"""Plugin for validating the non inline references"""

from collections import defaultdict
from numbers import Number
from typing import Union

from ghga_validator.core.models import ValidationMessage, ValidationResult
from ghga_validator.linkml.object_iterator import ObjectIterator
from ghga_validator.plugins.base_plugin import ValidationPlugin
from ghga_validator.schema_utils import get_range_class
from ghga_validator.utils import path_as_string


# pylint: disable=too-many-locals
class RefValidationPlugin(ValidationPlugin):
    """
    Plugin to check whether the values in non inline reference fields point
    to existing objects.
    """

    NAME = "RefValidationPlugin"

    def validate(self, data: dict, target_class: str) -> ValidationResult:
        """
        Perform validation on an object.

        Args:
            data: The object to validate
            target_class: class name for root class

        Returns:
            ValidationResult: A validation result that describes the outcome of validation

        """
        all_class_ids = self.get_all_class_ids(data, target_class)
        messages = self.validate_refs(data, target_class, all_class_ids)

        valid = len(messages) == 0

        result = ValidationResult(
            plugin_name=self.NAME, valid=valid, validation_messages=messages
        )
        return result

    def get_all_class_ids(self, obj: dict, target_class: str) -> dict[str, list[str]]:
        """Get all lists of identifies of inlined objects organized by class name

        Args:
            obj (Dict): The object to be parsed
            target_class (str): Target class

        Returns:
            Dict[class_name, List[str]]: The dictionary containing the lists of
            identifiers by the class name
        """
        all_ids = defaultdict(list)

        for class_name, identifier, _, _ in ObjectIterator(
            self.schema, obj, target_class
        ):
            all_ids[class_name].append(identifier)

        return all_ids

    def validate_refs(
        self,
        object_to_validate: dict,
        target_class: str,
        all_class_ids: dict,
    ) -> list[ValidationMessage]:
        """
        Validate non inlined reference fields in the JSON data

        Args:
            object_to_validate: input data
            target_class: parent class in the schema
            all_class_ids: pre-computed dictionary containing all identifiers ordered by class

        Returns:
            List[ValidationMessage]: List of validation messages

        """
        messages = []

        for class_name, _, data, path in ObjectIterator(
            self.schema, object_to_validate, target_class
        ):
            for field, value in data.items():
                slot_def = self.schema.induced_slot(field, class_name)
                range_class = get_range_class(self.schema, slot_def)
                if range_class and not self.schema.is_inlined(slot_def):
                    non_match = self.find_missing_refs(
                        value, all_class_ids[range_class]
                    )
                    if len(non_match) == 0:
                        continue
                    message = ValidationMessage(
                        message="Unknown reference(s) " + str(non_match),
                        field=f"{path_as_string(path)}.{field}",
                        value=value,
                    )
                    messages.append(message)
        return messages

    def find_missing_refs(
        self,
        ref_value: Union[list[Union[Number, str]], Union[Number, str]],
        id_list: list,
    ) -> list:
        """
        Search for missing references

        Returns:
            List: List of missing references
        """
        if not isinstance(ref_value, list):
            return [ref_value] if ref_value not in id_list else []
        return [x for x in ref_value if x not in id_list]
