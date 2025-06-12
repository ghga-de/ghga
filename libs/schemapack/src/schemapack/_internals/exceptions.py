# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Collection of package-specific exceptions"""

from abc import ABC
from dataclasses import dataclass
from enum import Enum

import pydantic_core


class SpecType(str, Enum):
    """An enumeration of the types of specs."""

    SCHEMAPACK = "schemapack"
    DATAPACK = "datapack"


class BaseError(ABC, Exception):
    """Base class for all schemapack errors."""


class ParsingError(BaseError, ValueError):
    """Raised when parsing JSON or YAML data fails."""


class SpecError(BaseError, ValueError):
    """An error indicating that an instance was not valid against the specification."""

    def __init__(self, message: str, *, details: list[pydantic_core.ErrorDetails]):
        """Initiate a SpecError.

        Args:
            message: A human-readable message describing the error.
            details: Details on which fields of the instance are invalid.
        """
        super().__init__(message)
        self.message = message
        self.details = details


class SchemaPackSpecError(SpecError):
    """An error indicating that the provided data is not valid against the schemapack
    specification.
    """

    def __init__(self, message: str, *, details: list[pydantic_core.ErrorDetails]):
        """Initiate a SchemaPackSpecError.

        Args:
            message: A human-readable message describing the error.
            details: Details on which fields of the instance are invalid.
        """
        message = (
            "The provided object was not compatible with the schemapack"
            + f" specification: {message}"
        )
        super().__init__(message, details=details)


class DataPackSpecError(SpecError):
    """An error indicating that the provided data is not valid against the datapack
    specification (this is independent of validation done using a schemapack).
    """

    def __init__(self, message: str, *, details: list[pydantic_core.ErrorDetails]):
        """Initiate a SchemaPackSpecError.

        Args:
            message: A human-readable message describing the error.
            details: Details on which fields of the instance are invalid.
        """
        message = (
            "The provided object was not compatible with the datapack"
            + f" specification: {message}"
        )
        super().__init__(message, details=details)


class ValidationPluginError(BaseError, ValueError):
    """Raised by a ValidationPlugin."""

    def __init__(
        self, *, type_: str, message: str, details: dict[str, object] | None = None
    ):
        """Initiate a ValidationPluginError.

        Args:
            type: A preferably short type label.
            message: A human-readable message describing the error.
            details: A dictionary for transporting additional machine-readable details.
        """
        super().__init__(message)
        self.type_ = type_
        self.message = message
        self.details = details if details else {}


@dataclass
class ValidationErrorRecord:
    """A record of an Error occuring during validation on a specific context
    (e.g. a specific resource) regarding a specific validation aspect.

    Attributes:
        subject_class:
            If relevant, the name of the subject class as per the schemapack.
        subject_resource:
            If relevant, the ID or the subject resource of the subject class.
        type:
            A preferably short type label.
        message:
            A human-readable message describing the error.
        details:
            A dictionary for transporting additional machine-readable details.
    """

    subject_class: str | None
    subject_resource: str | None
    type: str
    message: str
    details: dict[str, object]


def _val_record_to_str(record: ValidationErrorRecord) -> str:
    """Translate a ValidationErrorRecords into a human-readable message
    to be displayed to the user on the terminal.
    """
    if record.subject_class:
        if record.subject_resource:
            context = f"resource '{record.subject_class}.{record.subject_resource}'"
        else:
            context = f"class '{record.subject_class}'"
    else:
        context = "global datapack"

    return (
        f"Error in {context}:"
        + f"\n\tType: {record.type}"
        + f"\n\tMessage: {record.message}"
    )


def _sorted_val_records(
    records: list[ValidationErrorRecord],
) -> list[ValidationErrorRecord]:
    """Sort a set of ValidationErrorRecords."""
    return sorted(records, key=lambda r: (r.subject_class, r.subject_resource, r.type))


class ValidationError(BaseError, ValueError):
    """A collection of ValidationErrorRecords raised when a datapack fails validation
    against a schemapack.
    """

    def __init__(self, records: list[ValidationErrorRecord]):
        """Initiate a ValidationError.

        Args:
            records: A list of ValidationErrorRecords.
        """
        if not records:
            raise ValueError("ValidationError must be raised with at least one record.")

        self.records = _sorted_val_records(records)
        n_records = len(self.records)
        record_messages = "\n".join(_val_record_to_str(r) for r in self.records)
        message = f"Validation failed with {n_records} issue(s):\n{record_messages}"

        super().__init__(message)


class ValidationAssumptionError(BaseError, RuntimeError):
    """This is raised when a unit of code assumes to work with a datapack that has
    already been validated against a specific schemapack, however, it became apparent
    that this assumption was not correct. The error should not contain the details on
    which aspect is invalid. These details can be retrieved by performing a validation
    and receiving a ValidationError.
    """

    def __init__(self, *, context: str):
        """Initiate a ValidationAssumptionError.

        Args:
            context: Some context to be included in the error message.
        """
        message = (
            "It was assumed that the provided datapack has already been validated"
            + " against the provided schemapack, however, this assumption failed in"
            + f" the context of {context}. Please validate the datapack against the"
            + " schemapack to get further details."
        )
        super().__init__(message)
        self.message = message


class CircularRelationError(BaseError, ValueError):
    """Raised when a circular relation between resources is detected, but the requested
    operation cannot be performed on datapacks with circular relations.
    """


class ClassNotFoundError(BaseError, KeyError):
    """Raised when a class was not found in a schemapack or datapack."""

    def __init__(self, *, class_name: str, spec_type: SpecType):
        """Initiate a ClassNotFoundError.

        Args:
            class_name:
                The name of the class that was not found.
            spec_type:
                The type of spec that the class was not found in.
        """
        message = f"Class '{class_name}' not found in the provided {spec_type.value}."
        super().__init__(message)
        self.class_name = class_name


class ResourceNotFoundError(BaseError, KeyError):
    """Raised when a resource was not found in a datapack."""

    def __init__(self, *, class_name: str, resource_id: str):
        """Initiate a ResourceNotFoundError.

        Args:
            class_name:
                The name of the class of the resource that was not found.
            resource_id:
                The ID of the resource that was not found.
        """
        message = (
            f"Resource of class '{class_name}' with id '{resource_id}' not found in"
            + " the provided datapack."
        )
        super().__init__(message)
        self.class_name = class_name
        self.resource_id = resource_id


class InvalidEmbeddingProfileError(BaseError, ValueError):
    """Raised when an embedding profile is invalid. A profile is invalid if the value
    of any key is neither a boolean nor a nested dictionary following the same rules
    recursively (i.e., the nested dictionary values must also be booleans or
    nested dictionaries).

    Invalid examples:

    A value that is neither a boolean nor a dictionary:
        {"some_relation": "this is not a boolean or a dictionary"}
    A nested dictionary containing invalid values (e.g., a string instead of a boolean):
        {"some_relation": {"nested_relation": "this is not a boolean"}}

    Valid examples:
        {"some_relation": True}
        {"some_relation": {"nested_relation": False}}
        {"some_relation": {"nested_relation": {"another_nested_relation": True}}}
    """
