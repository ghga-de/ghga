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

"""Event publisher code"""

from ghga_event_schemas.configs import AuditEventsConfig
from ghga_event_schemas.pydantic_ import AuditRecord
from hexkit.protocols.eventpub import EventPublisherProtocol

from uos.ports.outbound.event_pub import EventPublisherPort


class EventPubConfig(AuditEventsConfig):
    """Config for publishing events"""


class EventPubTranslator(EventPublisherPort):
    """A hexkit translator for publishing to the audit log."""

    def __init__(self, *, config: EventPubConfig, provider: EventPublisherProtocol):
        """Initialize with configs and a provider of the EventPublisherProtocol."""
        self._config = config
        self._provider = provider

    async def publish_audit_record(self, audit_record: AuditRecord) -> None:
        """Publish an audit record event"""
        payload = audit_record.model_dump(mode="json")
        await self._provider.publish(
            payload=payload,
            type_=self._config.audit_record_type,
            topic=self._config.audit_record_topic,
            key=f"uos-{audit_record.id}",
        )
