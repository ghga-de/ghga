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

"""Test the upload box priority payload schema."""

import pytest

from ghga_event_schemas.pydantic_ import UploadBoxPriority
from ghga_event_schemas.validation import (
    EventSchemaValidationError,
    get_validated_payload,
)

EXAMPLE_PAYLOAD = {
    "id": "global",
    "version": 7,
    "changed_by": "2b6f1c9e-3d4a-4e5b-8c7d-9e0f1a2b3c4d",
    "last_changed": "2026-10-14T13:02:11.482Z",
    "entries": [
        {
            "research_data_upload_box_id": "4f0b3c1e-8a9d-4b7e-9c2a-1d3e5f7a9b0c",
            "file_upload_box_id": "a1c2e3f4-5b6d-4e8f-9a0b-1c2d3e4f5a6b",
        },
        {
            "research_data_upload_box_id": "7d8e9f0a-1b2c-4d3e-8f4a-5b6c7d8e9f0a",
            "file_upload_box_id": "0e1f2a3b-4c5d-4e6f-8a7b-9c0d1e2f3a4b",
        },
    ],
}


def test_example_payload():
    """Test that the example payload from the Shoebill epic is valid."""
    priority = get_validated_payload(payload=EXAMPLE_PAYLOAD, schema=UploadBoxPriority)
    assert [str(entry.file_upload_box_id) for entry in priority.entries] == [
        "a1c2e3f4-5b6d-4e8f-9a0b-1c2d3e4f5a6b",
        "0e1f2a3b-4c5d-4e6f-8a7b-9c0d1e2f3a4b",
    ]


def test_change_by_system():
    """Test that a change made by the system has no `changed_by`."""
    payload = {**EXAMPLE_PAYLOAD, "changed_by": None}
    priority = get_validated_payload(payload=payload, schema=UploadBoxPriority)
    assert priority.changed_by is None


@pytest.mark.parametrize("missing_field", ["version", "last_changed", "entries"])
def test_missing_field(missing_field: str):
    """Test that the required fields cannot be left out."""
    payload = {
        key: value for key, value in EXAMPLE_PAYLOAD.items() if key != missing_field
    }
    with pytest.raises(EventSchemaValidationError):
        get_validated_payload(payload=payload, schema=UploadBoxPriority)
