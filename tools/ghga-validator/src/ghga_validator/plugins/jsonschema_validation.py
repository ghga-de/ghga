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

"""Plugin for structural validation of a JSON object"""

import json

import jsonschema
from linkml.generators.jsonschemagen import JsonSchemaGenerator
from linkml_runtime.utils.schemaview import ClassDefinitionName

from ghga_validator.core.models import ValidationMessage, ValidationResult
from ghga_validator.plugins.base_plugin import ValidationPlugin
from ghga_validator.utils import path_as_string


class GHGAJsonSchemaValidationPlugin(ValidationPlugin):
    """Plugin for structural validation of a JSON object."""

    NAME = "GHGAJsonSchemaValidationPlugin"

    def validate(
        self, data: dict, target_class: ClassDefinitionName
    ) -> ValidationResult:
        """
        Perform validation on an object.

        Args:
            data: The JSON object to validate
            target_class: class name for root class

        Returns:
            ValidationResult: A validation result that describes the outcome of validation

        """
        json_schema = self.jsonschema_from_linkml(target_class)

        messages = []

        validator = jsonschema.Draft7Validator(json_schema)
        errors = validator.iter_errors(data)

        for error in errors:
            message = ValidationMessage(
                message=error.message,
                field=path_as_string(error.absolute_path),
                value=error.instance,
            )
            messages.append(message)
            for err in error.context:
                message = ValidationMessage(
                    message=err.message,
                    field=path_as_string(err.absolute_path),
                    value=err.instance,
                )
                messages.append(message)

        valid = len(messages) == 0

        result = ValidationResult(
            plugin_name=self.NAME, valid=valid, validation_messages=messages
        )
        return result

    def jsonschema_from_linkml(self, target_class: ClassDefinitionName) -> dict:
        """Generates JSON schema from a LinkML schema"""
        json_schema_as_string = JsonSchemaGenerator(
            schema=self.schema.schema, top_class=target_class
        ).serialize()
        json_schema = json.loads(json_schema_as_string)
        return json_schema
