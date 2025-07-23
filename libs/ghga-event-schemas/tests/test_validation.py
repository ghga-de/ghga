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

"""Test schema validation utils."""

import json
from typing import Any

import pytest
from pydantic import BaseModel

from ghga_event_schemas import __version__
from ghga_event_schemas.pydantic_ import UploadDateModel
from ghga_event_schemas.validation import (
    EventSchemaValidationError,
    get_validated_payload,
)


class ExampleSchema(BaseModel):
    """An example schema."""

    some_param: str
    another_param: int


def test_happy():
    """Test successful payload validation using a schema."""
    payload = {"some_param": "test", "another_param": 1234}

    validated_payload = get_validated_payload(payload=payload, schema=ExampleSchema)
    assert isinstance(validated_payload, ExampleSchema)


def test_failure():
    """Test failed payload validation using a schema."""
    payload = {"some_param": "test", "another_param": "test"}

    with pytest.raises(EventSchemaValidationError):
        _ = get_validated_payload(payload=payload, schema=ExampleSchema)


@pytest.mark.parametrize(
    "payload,assertions",
    [
        ({}, ["type=missing"]),
        ({"upload_date": True}, ["type=datetime", "should be a valid datetime"]),
    ],
)
def test_error_messages(payload: dict[str, Any], assertions: list[str]):
    """Verify that the pydantic error includes information as expected."""
    version_text = f"'UploadDateModel' from ghga-event-schemas v{__version__}"
    payload_text = f"The complete payload was: {json.dumps(payload)}"

    with pytest.raises(EventSchemaValidationError) as error:
        get_validated_payload(payload, UploadDateModel)

    error_text = str(error.value)

    for string in assertions:
        assert string in error_text
    assert "upload_date" in error_text
    assert version_text in error_text
    assert payload_text in error_text
