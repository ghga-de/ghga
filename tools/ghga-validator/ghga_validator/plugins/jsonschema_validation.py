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

import json
from typing import Dict

import jsonschema
from linkml.generators.jsonschemagen import JsonSchemaGenerator
from linkml_runtime.utils.schemaview import ClassDefinitionName
from linkml_validator.models import SeverityEnum, ValidationMessage, ValidationResult
from linkml_validator.plugins.base import BasePlugin

from ghga_validator.utils import path_as_string


class GHGAJsonSchemaValidationPlugin(BasePlugin):
    """
    Plugin for structural validation of a JSON object.

    Args:
        schema: Path or URL to schema YAML
        kwargs: Additional arguments that are used to instantiate the plugin

    """

    NAME = "GHGAJsonSchemaValidationPlugin"

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
        json_schema = self.jsonschema_from_linkml(target_class)

        messages = []

        validator = jsonschema.Draft7Validator(json_schema)
        errors = validator.iter_errors(obj)

        for error in errors:
            message = ValidationMessage(
                severity=SeverityEnum.error,
                message=error.message,
                field=path_as_string(error.absolute_path),
                value=error.instance,
            )
            messages.append(message)
            for err in error.context:
                message = ValidationMessage(
                    severity=SeverityEnum.error,
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

    def jsonschema_from_linkml(self, target_class: ClassDefinitionName) -> Dict:
        """
        Generates JSON schema from a LinkML schema
        """
        json_schema_as_string = JsonSchemaGenerator(
            schema=self.schema, top_class=target_class
        ).serialize()
        json_schema = json.loads(json_schema_as_string)
        return json_schema
