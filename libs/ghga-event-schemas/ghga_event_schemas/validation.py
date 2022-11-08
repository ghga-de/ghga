# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""Utils for validating event payloads against event schemas."""

import json
from typing import Any, Mapping, TypeVar

import pydantic

JsonObject = Mapping[str, Any]


class EventSchemaValidationError(ValueError):
    """Raised when an event schema failed to validate against an event schema."""

    def __init__(self, *, payload: JsonObject, schema: type[pydantic.BaseModel]):
        message = (
            "The the following event payload failed validation against the corresponding"
            + f" event schema. The payload was '{json.dumps(payload)}' but the schema"
            + f" was '{schema.schema_json()}."
        )
        super().__init__(message)


Schema = TypeVar("Schema", bound=pydantic.BaseModel)


def get_validated_payload(payload: JsonObject, schema: type[Schema]) -> Schema:
    """Validate an event payload against a specified pydantic-based event schema
    and return the validated pydantic model."""

    try:
        return schema(**payload)
    except pydantic.ValidationError as error:
        raise EventSchemaValidationError(payload=payload, schema=schema) from error
