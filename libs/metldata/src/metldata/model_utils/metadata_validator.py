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

"""Logic to validate submission metadata based on a LinkML model."""

from functools import lru_cache
from typing import Any

from linkml_validator.models import ValidationMessage
from linkml_validator.validator import Validator

from metldata.model_utils.essentials import MetadataModel


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
def get_metadata_validator(model: MetadataModel):
    """Create a validator for the given metadata model."""
    with model.temporary_yaml_path() as model_path:
        return Validator(schema=str(model_path))


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

        validation_report = validator.validate(metadata, target_class="Submission")

        if not validation_report.valid:
            issues = [
                message
                for result in validation_report.validation_results
                if not result.valid and result.validation_messages is not None
                for message in result.validation_messages
            ]
            raise MetadataValidationError(issues=issues)
