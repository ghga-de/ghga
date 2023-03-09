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

from pathlib import Path
from typing import Any

from linkml_runtime.utils.schemaview import SchemaView
from linkml_validator.models import ValidationMessage
from linkml_validator.validator import Validator

from metldata.shared.config import MetadataModelConfig


class MetadataValidatorConfig(MetadataModelConfig):
    """Config parameters and their defaults."""


class MetadataModelAssumptionError(RuntimeError):
    """Raised when the basic assumptions that metldata makes about the metadata model
    are not met"""


def check_metadata_model_assumption(*, model_path: Path) -> None:
    """Check that the basic assumptions that metldata makes about the metadata model
    are met. Raises a MetadataModelAssumptionError otherwise."""

    schema_view = SchemaView(schema=str(model_path))

    # has a submission class that is the tree root:
    submission_class = schema_view.get_class(class_name="Submission", imports=False)

    if submission_class is None:
        raise MetadataModelAssumptionError(
            "A submission class is required but does not exist."
        )

    if not submission_class.tree_root:
        raise MetadataModelAssumptionError(
            "The submission class must have the tree_root property set to true."
        )


class MetadataValidator:
    """Validating metadata against a LinkML model."""

    class ValidationError(RuntimeError):
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

    def __init__(self, *, config: MetadataValidatorConfig):
        """Initialize the validator with a LinkML model."""

        check_metadata_model_assumption(model_path=config.metadata_model)

        self._validator = Validator(schema=str(config.metadata_model))

    def validate(self, metadata: dict[str, Any]) -> None:
        """Validate metadata against the provided model.

        Raises:
            ValidationError: When validation failed.
        """

        validation_report = self._validator.validate(
            metadata, target_class="Submission"
        )

        if not validation_report.valid:
            issues = [
                message
                for result in validation_report.validation_results
                if not result.valid and result.validation_messages is not None
                for message in result.validation_messages
            ]
            raise self.ValidationError(issues=issues)
