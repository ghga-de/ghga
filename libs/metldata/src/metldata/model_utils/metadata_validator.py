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
from collections import defaultdict
from collections.abc import Iterable, Iterator
from functools import lru_cache
from typing import Any

import jsonschema
from linkml.generators.jsonschemagen import JsonSchemaGenerator
from linkml_validator.models import SeverityEnum, ValidationMessage

from metldata.metadata_utils import lookup_self_id, normalize_alias
from metldata.model_utils.anchors import get_anchors_points_by_target
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


def raise_on_errors(errors: Iterable[tuple[str, str | None, Any]]) -> None:
    """Raise a MetadataValidationError with one issue per (message, field, value),
    if there is any.
    """
    issues = [
        ValidationMessage(
            severity=SeverityEnum.error, message=message, field=field, value=value
        )
        for message, field, value in errors
    ]
    if issues:
        raise MetadataValidationError(issues=issues)


def describe_error(error: jsonschema.ValidationError) -> str:
    """Describe a validation error, spelling out list-length limits such as the
    cardinality of a slot.
    """
    if error.validator in ("minItems", "maxItems") and isinstance(error.instance, list):
        limit = "at least" if error.validator == "minItems" else "at most"
        return (
            f"holds {len(error.instance)} entries, but the model allows"
            + f" {limit} {error.validator_value}"
        )

    return error.message


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

        raise_on_errors(
            (
                describe_error(error),
                ".".join(map(str, error.absolute_path)) or None,
                error.instance if not isinstance(error.instance, dict) else None,
            )
            for error in sorted(validator.iter_errors(metadata), key=str)
        )

    def _iter_aliases(self, metadata: dict[str, Any]) -> Iterator[tuple[str, str]]:
        """Iterate over the alias and the class of every entity of the metadata."""
        for anchor_point in get_anchors_points_by_target(model=self._model).values():
            for resource in metadata.get(anchor_point.root_slot, []):
                alias = lookup_self_id(
                    resource=resource, identifier_slot=anchor_point.identifier_slot
                )
                yield alias, anchor_point.target_class

    def check_aliases_are_ascii(self, metadata: dict[str, Any]) -> None:
        """Check that every alias of the submitted metadata holds ASCII characters
        only, since accessions '{study_pid}.{alias}' are built from it.

        Raises:
            ValidationError: naming each alias that is not ASCII, with its class.
        """
        raise_on_errors(
            (
                f"the alias of an entity of the class '{class_name}' must hold ASCII"
                + " characters only",
                "alias",
                alias,
            )
            for alias, class_name in self._iter_aliases(metadata)
            if not alias.isascii()
        )

    def check_alias_uniqueness(self, metadata: dict[str, Any]) -> None:
        """Check that no two entities of the submitted metadata share a normalized
        alias, across all classes, since accessions '{study_pid}.{alias}' take the
        normalized alias and drop the class.

        For submitted metadata only: transformed metadata may embed one entity in
        several places, repeating its alias. Expects ASCII aliases, as checked by
        `check_aliases_are_ascii`, since normalizing would mask other characters.

        Raises:
            ValidationError: naming the original aliases of each shared normalized
                alias, with the classes of the entities sharing it.
        """
        entities_by_alias: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for alias, class_name in self._iter_aliases(metadata):
            entities_by_alias[normalize_alias(alias)].append((alias, class_name))

        raise_on_errors(
            (
                f"the alias is used by {len(entities)} entities, of the class(es) "
                + ", ".join(sorted({f"'{class_name}'" for _, class_name in entities}))
                + ", but must be unique across the submission",
                "alias",
                ", ".join(sorted({alias for alias, _ in entities})),
            )
            for _, entities in sorted(entities_by_alias.items())
            if len(entities) > 1
        )
