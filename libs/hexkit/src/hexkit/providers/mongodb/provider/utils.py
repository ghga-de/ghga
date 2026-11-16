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

"""MongoDB-based provider utilities.

Utilities for testing are located in `../testutils.py`.
"""

from collections.abc import Mapping
from contextlib import contextmanager
from typing import Annotated, Any

from pydantic import BaseModel, TypeAdapter, ValidationError
from pymongo.errors import DocumentTooLarge, PyMongoError

from hexkit.protocols.dao import DaoError, DbTimeoutError, Dto, InvalidChangesError

__all__ = [
    "document_to_dto",
    "dto_to_document",
    "split_changes",
    "translate_pymongo_errors",
]


@contextmanager
def translate_pymongo_errors():
    """Catch PyMongoError and re-raise it as DbTimeoutError if it is a timeout error.

    Non-timeout errors are re-raised as DaoError, and so is DocumentTooLarge, which
    pymongo raises for a document or filter over 16 MB and which is no PyMongoError.
    """
    try:
        yield
    except PyMongoError as exc:
        if exc.timeout:  # denotes timeout-related errors in pymongo
            raise DbTimeoutError(str(exc)) from exc
        raise DaoError(str(exc)) from exc
    except DocumentTooLarge as exc:
        raise DaoError(str(exc)) from exc


def document_to_dto(
    document: dict[str, Any], *, id_field: str, dto_model: type[Dto]
) -> Dto:
    """Converts a document obtained from the MongoDB database into a DTO model-
    compliant representation.
    """
    document[id_field] = document.pop("_id")
    return dto_model.model_validate(document)


def dto_to_document(dto: Dto, *, id_field: str) -> dict[str, Any]:
    """Converts a DTO into a representation that is a compatible document for a
    MongoDB Database.

    If there is a non-serializable field in the DTO, it will raise an error.
    Such DTOs should implement appropriate serialization methods or use a different
    data type for the field.
    """
    document = dto.model_dump()
    document["_id"] = document.pop(id_field)

    return document


def split_changes(
    changes: Mapping[str, Any], *, dto_model: type[BaseModel], id_field: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split the `changes` of an `update_first` call into the serialized values of
    model fields and the update operators.

    Each plain value is validated against the type of its field and serialized the
    same way as in `dto_to_document`. The values of update operators are passed on
    as they are.

    Returns:
        A tuple of a mapping from field names to serialized values and a mapping
        from operators (keys starting with `$`) to their values.

    Raises:
        InvalidChangesError:
            If `changes` is empty, names the ID field or a field that is not in
            the model, or contains a value that doesn't fit its field.
    """
    if not changes:
        raise InvalidChangesError("The provided changes were empty.")

    validated_values: dict[str, Any] = {}
    operators: dict[str, Any] = {}
    for key, value in changes.items():
        if key.startswith("$"):
            operators[key] = value
            continue
        if key == id_field:
            raise InvalidChangesError(
                f"The provided changes were invalid: the ID field '{id_field}'"
                + " cannot be changed."
            )
        field_info = dto_model.model_fields.get(key)
        if field_info is None:
            raise InvalidChangesError(
                f"The provided changes were invalid: '{key}' is not a field of"
                + f" {dto_model.__name__}."
            )
        field_type: Any = field_info.annotation
        for constraint in field_info.metadata:
            field_type = Annotated[field_type, constraint]
        adapter: TypeAdapter = TypeAdapter(field_type)
        try:
            validated_values[key] = adapter.validate_python(value)
        except ValidationError as error:
            raise InvalidChangesError(
                f"The provided changes were invalid: the value for '{key}' does"
                + f" not fit the field: {error}"
            ) from error

    # Serializing through the model applies its field serializers, as `model_dump`
    # does for a whole DTO
    field_values = dto_model.model_construct(**validated_values).model_dump(
        include=set(validated_values)
    )
    return field_values, operators
