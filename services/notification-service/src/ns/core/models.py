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
"""Contains models for the notification service."""

from pydantic import BaseModel, Field


class NotificationRecord(BaseModel):
    """Model for tracking which notifications have been sent.

    The hash sum is used to identify the notification event content and the sent flag
    indicates if the notification has been sent.
    """

    hash_sum: str = Field(..., description="Hash sum of notification event")
    sent: bool = Field(
        ..., description="Flag indicating if the notification has been sent"
    )
