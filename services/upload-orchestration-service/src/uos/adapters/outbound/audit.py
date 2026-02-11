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
"""Implementation of audit logging class"""

from typing import Literal

from ghga_event_schemas.pydantic_ import AuditRecord
from hexkit.correlation import get_correlation_id
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from uos.core.models import ResearchDataUploadBox
from uos.ports.outbound.audit import AuditRepositoryPort
from uos.ports.outbound.event_pub import EventPublisherPort


class AuditRepository(AuditRepositoryPort):
    """Audit record repository class to track changes to important domain objects."""

    def __init__(self, *, service: str, event_publisher: EventPublisherPort):
        """Set up the AuditRepository"""
        self._publisher = event_publisher
        self._service = service

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
        correlation_id = get_correlation_id()
        audit_record = AuditRecord(
            service=self._service,
            correlation_id=correlation_id,
            created=now_utc_ms_prec(),
            label=label,
            description=description,
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
        )
        await self._publisher.publish_audit_record(audit_record)

    async def log_box_created(
        self, *, box: ResearchDataUploadBox, user_id: UUID4
    ) -> None:
        """Log the creation of a ResearchDataUploadBox"""
        await self.create_audit_record(
            label="ResearchDataUploadBox created",
            description=f"A new ResearchDataUploadBox was created with '{box.title}' (ID: {box.id}).",
            user_id=user_id,
            action="C",
            entity=ResearchDataUploadBox.__name__,
            entity_id=str(box.id),
        )

    async def log_box_updated(
        self, *, box: ResearchDataUploadBox, user_id: UUID4
    ) -> None:
        """Log changes made to a ResearchDataUploadBox"""
        await self.create_audit_record(
            label="ResearchDataUploadBox updated",
            description=f"ResearchDataUploadBox '{box.title}' (ID: {box.id}) was updated. New state: {box.state}.",
            user_id=user_id,
            action="U",
            entity=ResearchDataUploadBox.__name__,
            entity_id=str(box.id),
        )

    async def log_access_granted(
        self, *, box_id: UUID4, grantor_id: UUID4, grantee_id: UUID4
    ):
        """Log that a user was granted access to a ResearchDataUploadBox"""
        await self.create_audit_record(
            label="Access granted to ResearchDataUploadBox",
            description=f"User {grantee_id} was granted access by user {grantor_id}"
            + f" to ResearchDataUploadBox {box_id}.",
            user_id=grantor_id,
            action=None,
            entity=ResearchDataUploadBox.__name__,
            entity_id=str(box_id),
        )
