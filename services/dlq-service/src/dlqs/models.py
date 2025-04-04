# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Models for the DLQ Service"""

from typing import Any

from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc
from pydantic import UUID4, BaseModel, Field


class EventHeaders(BaseModel):
    """Model representing the headers for an event"""

    headers: dict[str, str] = Field(
        ...,
        description="Any headers for the event. Must at least include correlation ID.",
    )


class EventCore(BaseModel):
    """Model representing the core GHGA-internal event info"""

    topic: str = Field(
        ..., description="The name of the original topic the event was located in."
    )
    type_: str = Field(..., description="The 'type' given to the original event.")
    payload: dict[str, Any] = Field(..., description="The payload for the event.")
    key: str = Field(..., description="The key of the event.")


class PublishableEventData(EventCore, EventHeaders):
    """Only the data needed to publish an event -- core data and headers"""


class RawDLQEvent(EventCore, EventHeaders):
    """The core GHGA-internal event info + headers and timestamp, consumed from Kafka"""

    timestamp: UTCDatetime = Field(
        default_factory=now_as_utc, description="The timestamp of the event."
    )


class DLQInfo(BaseModel):
    """Extra DLQ-specific information for a DLQ event"""

    service: str = Field(
        ..., description="The name of the service that failed to process the event."
    )
    partition: int = Field(..., description="The partition of the event.")
    offset: int = Field(..., description="The offset of the event.")
    exc_class: str = Field("", description="The exception class that was raised.")
    exc_msg: str = Field("", description="The exception message that was raised.")


class StoredDLQEvent(RawDLQEvent):
    """Model representing a DLQ event as it exists in the database"""

    dlq_id: UUID4 = Field(..., description="The unique DLQS identifier for a DLQ event")
    dlq_info: DLQInfo = Field(..., description="The DLQ information for the DLQ event")
