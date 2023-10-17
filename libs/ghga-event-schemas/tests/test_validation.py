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

"""Test schema validation utils."""

from datetime import datetime

import pytest
from pydantic import BaseModel

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


def test_datetime_validation_happy():
    """Check validation hook for upload date - happy path"""
    payload = {"upload_date": datetime.utcnow().isoformat()}
    validated_payload = get_validated_payload(payload=payload, schema=UploadDateModel)
    assert isinstance(validated_payload, UploadDateModel)


def test_datetime_validation_failure():
    """Check validation hook for upload date with invalid string"""
    payload = {"upload_date": "test o'clock"}
    with pytest.raises(EventSchemaValidationError):
        _ = get_validated_payload(payload=payload, schema=UploadDateModel)
