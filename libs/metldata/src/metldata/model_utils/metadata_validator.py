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
#

"""Logic to validate submission metadata based on a LinkML model."""

import json
from functools import lru_cache
from typing import Any

import jsonschema
from linkml.generators.jsonschemagen import JsonSchemaGenerator
from linkml_validator.models import SeverityEnum, ValidationMessage

from metldata.model_utils.essentials import ROOT_CLASS, MetadataModel


class InvalidMetadataError(RuntimeError):
    """Raised when the metadata is invalid."""


class MetadataValidationError(InvalidMetadataError):
    """Raised when the validation of metadata against the provided model fails."""

    def __init__(self, *, issues: list[ValidationMessage]):
        """Initializes with list of issues."""
        self.issues = issues

        message = "Validation failed due to following issues: " + ", ".join(
            (
                f"in field '{issue.field}' with value '{issue.value}': {issue.message}"
                + f" ({issue.severity})"
            )
            for issue in self.issues
        )
        super().__init__(message)


@lru_cache
def get_metadata_validator(model: MetadataModel) -> jsonschema.Draft7Validator:
    """Create a JSON Schema validator for the root class of the given metadata model.

    The JSON Schema is generated directly from the in-memory model via LinkML's
    JsonSchemaGenerator. This deliberately avoids `linkml_validator.Validator`, which
    additionally compiles a full Python module from the schema (via PythonGenerator)
    just to look up the target class name - an expensive step that dominated validator
    construction - and which required serializing the model to a temporary YAML file
    only to parse it back in. Generating the schema once from the in-memory model and
    validating with `jsonschema` yields identical accept/reject behaviour at a fraction
    of the cost. The result is cached per model.
    """
    generator = JsonSchemaGenerator(
        schema=model,
        top_class=ROOT_CLASS,
        mergeimports=True,
        not_closed=False,
    )
    schema = json.loads(generator.serialize())
    return jsonschema.Draft7Validator(schema)


class MetadataValidator:
    """Validating metadata against a LinkML model."""

    # error shortcuts:
    ValidationError = MetadataValidationError

    def __init__(self, *, model: MetadataModel):
        """Initialize the validator with a metadata model."""
        self._model = model

    def validate(self, metadata: dict[str, Any]) -> None:
        """Validate metadata against the provided model.

        Raises:
            ValidationError: When validation failed.
        """
        validator = get_metadata_validator(self._model)

        errors = sorted(validator.iter_errors(metadata), key=str)

        if errors:
            issues = [
                ValidationMessage(
                    severity=SeverityEnum.error,
                    message=error.message,
                    field=(
                        ".".join(map(str, error.absolute_path))
                        if error.absolute_path
                        else None
                    ),
                    value=(
                        error.instance if not isinstance(error.instance, dict) else None
                    ),
                )
                for error in errors
            ]
            raise MetadataValidationError(issues=issues)
