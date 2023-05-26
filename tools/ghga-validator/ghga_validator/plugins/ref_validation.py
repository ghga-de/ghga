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

from collections import defaultdict
from numbers import Number
from typing import Dict, List, Union

from linkml_runtime.utils.schemaview import SchemaView
from linkml_validator.models import SeverityEnum, ValidationMessage, ValidationResult
from linkml_validator.plugins.base import BasePlugin

from ghga_validator.linkml.object_iterator import ObjectIterator
from ghga_validator.schema_utils import get_range_class
from ghga_validator.utils import path_as_string


# pylint: disable=too-many-locals
class RefValidationPlugin(BasePlugin):
    """
    Plugin to check whether the values in non inline reference fields point
    to existing objects.

    Args:
        schema: Path or URL to schema YAML
        kwargs: Additional arguments that are used to instantiate the plugin

    """

    NAME = "RefValidationPlugin"

    def __init__(self, schema: str) -> None:
        super().__init__(schema)
        self.schemaview = SchemaView(schema)

    def process(self, obj: Dict, **kwargs) -> ValidationResult:
        """
        Perform validation on an object.

        Args:
            obj: The object to validate
            kwargs: Additional arguments that are used for processing

        Returns:
            ValidationResult: A validation result that describes the outcome of validation

        """
        target_class = kwargs["target_class"]

        all_class_ids = self.get_all_class_ids(obj, target_class)
        messages = self.validate_refs(obj, target_class, all_class_ids)

        valid = len(messages) == 0

        result = ValidationResult(
            plugin_name=self.NAME, valid=valid, validation_messages=messages
        )
        return result

    def get_all_class_ids(self, obj: Dict, target_class: str) -> Dict[str, List[str]]:
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
            self.schemaview, obj, target_class
        ):
            all_ids[class_name].append(identifier)

        return all_ids

    def validate_refs(
        self,
        object_to_validate: Dict,
        target_class: str,
        all_class_ids: Dict,
    ) -> List[ValidationMessage]:
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
            self.schemaview, object_to_validate, target_class
        ):
            for field, value in data.items():
                slot_def = self.schemaview.induced_slot(field, class_name)
                range_class = get_range_class(self.schemaview, slot_def)
                if range_class and not self.schemaview.is_inlined(slot_def):
                    non_match = self.find_missing_refs(
                        value, all_class_ids[range_class]
                    )
                    if len(non_match) == 0:
                        continue
                    message = ValidationMessage(
                        severity=SeverityEnum.error,
                        message="Unknown reference(s) " + str(non_match),
                        field=f"{path_as_string(path)}.{field}",
                        value=value,
                    )
                    messages.append(message)
        return messages

    def find_missing_refs(
        self,
        ref_value: Union[List[Union[Number, str]], Union[Number, str]],
        id_list: List,
    ) -> List:
        """
        Search for missing references

        Returns:
            List: List of missing references
        """
        if not isinstance(ref_value, list):
            return [ref_value] if ref_value not in id_list else []
        return [x for x in ref_value if x not in id_list]
