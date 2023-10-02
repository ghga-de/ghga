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

"""Test validation logic of pydantic models."""

from contextlib import nullcontext

import pytest
from pydantic import ValidationError

from ghga_service_commons.httpyexpect.models import HttpExceptionBody


@pytest.mark.parametrize(
    "exception_id, description, data, is_valid",
    [
        ("testException1", "My test description.", {"test": "test"}, True),
        # Id starts with number:
        ("1testException", "My test description.", {"test": "test"}, False),
        # Id to short:
        ("te", "My test description.", {"test": "test"}, False),
        # Id uses non allowed characters:
        ("teßtException", "My test description.", {"test": "test"}, False),
        # Id is too long:
        (
            "TestExceptionWithABitMoreThan40Characters",
            "My test description.",
            {"test": "test"},
            False,
        ),
        # A string as data:
        ("testException1", "My test description.", "test", False),
    ],
)
def test_http_exception_body(
    exception_id: str, description: str, data: dict, is_valid: bool
):
    """Test validation logic of the HTTPExceptionBody model."""
    with nullcontext() if is_valid else pytest.raises(ValidationError):
        HttpExceptionBody(exception_id=exception_id, description=description, data=data)
