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
"""Models used in the SMS"""

from collections.abc import Mapping
from typing import Any

from pydantic import UUID4, BaseModel, Field

DocumentType = Mapping[str, Any]
Criteria = Mapping[str, Any]


class UpsertionDetails(BaseModel):
    """Details for upserting documents in a collection."""

    id_field: str = Field(
        default="_id", description="The field to use as the document id."
    )
    documents: DocumentType | list[DocumentType] = Field(
        default=..., description="The document(s) to upsert."
    )


class EventDetails(BaseModel):
    """Details for publishing events."""

    payload: Mapping[str, str] = Field(
        default=..., description="The value of the event."
    )
    topic: str = Field(default=..., description="The topic to publish the event to.")
    type_: str = Field(default=..., description="The type of the event.")
    key: str = Field(default=..., description="The key of the event.")
    event_id: UUID4 | None = Field(default=None, description="The event ID to use.")
    headers: Mapping[str, str] | None = Field(
        None, description="The headers for the event."
    )
