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
#

"""A validation plugin."""

import json

import jsonschema.exceptions
import jsonschema.protocols
import jsonschema.validators

from schemapack.exceptions import ValidationPluginError
from schemapack.spec.datapack import DataPack, Resource, ResourceId
from schemapack.spec.schemapack import ClassDefinition
from schemapack.validation.base import ResourceValidationPlugin


def _get_json_schema_validator(schema_str: str) -> jsonschema.protocols.Validator:
    """Get a JSON Schema validator for the given schema formatted as JSON string.
    It is assumed that the schema has already been checked for validity against the
    JSON Schema specs.
    """
    schema = json.loads(schema_str)
    cls: type[jsonschema.protocols.Validator] = jsonschema.validators.validator_for(
        schema
    )
    return cls(schema)


class ContentSchemaValidationPlugin(ResourceValidationPlugin):
    """A resource-scoped validation plugin validating the content of one resource
    against the content JSON Schema defined in the corresponding schemapack.
    """

    @staticmethod
    def does_apply(*, class_: ClassDefinition) -> bool:
        """A classmethod to check whether this validation plugin is relevant for the
        given schemapack.

        Returns: True if this plugin is relevant for the given class definition.
        """
        # Is always relevant since all resources must have a content schema:
        return True

    def __init__(self, *, class_: ClassDefinition):
        """This plugin is configured with one specific class definition of a schemapack."""
        self._json_schema_validator = _get_json_schema_validator(
            class_.content.json_schema
        )

    def validate(
        self, *, resource: Resource, resource_id: ResourceId, datapack: DataPack
    ):
        """Validates a specific resource of the defined class. The entire datapack is
        provided for resolving relations to resources of other classes.

        Raises:
            schemapack.exceptions.DataValidationError: If validation fails.
        """
        try:
            self._json_schema_validator.validate(resource.content)
        except jsonschema.exceptions.ValidationError as error:
            raise ValidationPluginError(
                type_="ContentValidationError", message=error.message
            ) from error
