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

"""Event subscriber logic"""

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_event_schemas.configs.stateful import ArtifactEventsConfig
from hexkit.protocols.daosub import DaoSubscriberProtocol

from rts.ports.inbound.rev_tran import ReverseTranspilerPort


class OutboxSubTranslatorConfig(ArtifactEventsConfig):
    """Config for the event subscriber"""


class OutboxSubTranslator(DaoSubscriberProtocol[event_schemas.Artifact]):
    """Outbox subscriber that translates events for the reverse transpiler"""

    event_topic: str
    dto_model = event_schemas.Artifact

    def __init__(
        self,
        *,
        config: OutboxSubTranslatorConfig,
        reverse_transpiler: ReverseTranspilerPort,
    ):
        self._config = config
        self._orchestrator = reverse_transpiler
        self.event_topic = config.artifact_topic

    async def changed(self, resource_id: str, update: event_schemas.User) -> None:
        """Consume change event (created or updated) for an artifact."""
        pass

    async def deleted(self, resource_id: str) -> None:
        """Consume event indicating the deletion of an artifact."""
        pass
