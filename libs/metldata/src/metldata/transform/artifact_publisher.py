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

"""Logic for publishing artifacts."""


import json

from hexkit.protocols.eventpub import EventPublisherProtocol
from pydantic import BaseModel

from metldata.event_handling.artifact_events import (
    ArtifactEventConfig,
    get_artifact_topic,
)
from metldata.event_handling.models import SubmissionEventPayload


class ArtifactEventPublisherConfig(ArtifactEventConfig):
    """Config parameters and their defaults."""


class ArtifactEvent(BaseModel):
    """Artifact event model."""

    artifact_type: str
    payload: SubmissionEventPayload


class ArtifactEventPublisher:
    """Handles publication of artifact events."""

    def __init__(
        self, *, config: ArtifactEventPublisherConfig, provider: EventPublisherProtocol
    ):
        """Initialize with config parameters."""
        self._config = config
        self._provider = provider

    async def publish_artifact(self, artifact_event: ArtifactEvent):
        """Publish an artifact as submission event"""
        payload = json.loads(artifact_event.payload.model_dump_json())
        topic = get_artifact_topic(
            artifact_topic_prefix=self._config.artifact_topic_prefix,
            artifact_type=artifact_event.artifact_type,
        )
        type_ = artifact_event.artifact_type

        await self._provider.publish(
            topic=topic,
            type_=type_,
            key=artifact_event.payload.submission_id,
            payload=payload,
        )
