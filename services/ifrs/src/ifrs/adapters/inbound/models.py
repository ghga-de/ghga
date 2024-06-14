# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Models for inbound adapter idempotence functionality"""

from ghga_event_schemas import pydantic_ as event_schemas
from pydantic import BaseModel, Field


class IdempotenceRecord(BaseModel):
    """A record of an event for idempotence purposes."""

    correlation_id: str = Field(
        default=...,
        description="The correlation ID associated with the request event.",
    )


class NonStagedFileRequestedRecord(
    IdempotenceRecord, event_schemas.NonStagedFileRequested
):
    """A record of a NonStagedFileRequested event for idempotence purposes."""


class FileDeletionRequestedRecord(
    IdempotenceRecord, event_schemas.FileDeletionRequested
):
    """A record of a FileDeletionRequested event for idempotence purposes."""


class FileUploadValidationSuccessRecord(
    IdempotenceRecord, event_schemas.FileUploadValidationSuccess
):
    """A record of a FileUploadValidationSuccess event for idempotence purposes."""
