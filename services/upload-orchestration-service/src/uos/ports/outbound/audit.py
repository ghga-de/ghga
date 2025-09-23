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

"""Port definition for audit logging class"""

from abc import ABC, abstractmethod
from typing import Literal

from ghga_event_schemas.pydantic_ import ResearchDataUploadBox
from pydantic import UUID4


class AuditRepositoryPort(ABC):
    """Port for audit record repository operations."""

    @abstractmethod
    async def create_audit_record(  # noqa: PLR0913
        self,
        *,
        label: str,
        description: str,
        user_id: UUID4 | None = None,
        action: Literal["C", "R", "U", "D"] | None,
        entity: str | None,
        entity_id: str | None,
    ) -> None:
        """Create a new audit record and publish it as an event"""
        ...

    @abstractmethod
    async def log_box_created(
        self, *, box: ResearchDataUploadBox, user_id: UUID4
    ) -> None:
        """Log the creation of a ResearchDataUploadBox"""

    @abstractmethod
    async def log_box_updated(
        self, *, box: ResearchDataUploadBox, user_id: UUID4
    ) -> None:
        """Log changes made to a ResearchDataUploadBox"""
        ...

    @abstractmethod
    async def log_access_granted(
        self, *, box_id: UUID4, grantor_id: UUID4, grantee_id: UUID4
    ):
        """Log that a user was granted access to a ResearchDataUploadBox"""
