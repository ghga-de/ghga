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

"""Logic for the publication of source events."""

import asyncio
import json

from hexkit.protocols.eventpub import EventPublisherProtocol

from metldata.event_handling.models import SubmissionAnnotation, SubmissionEventPayload
from metldata.event_handling.submission_events import SourceEventConfig
from metldata.submission_registry import models


class SourceEventPublisherConfig(SourceEventConfig):
    """Config parameters and their defaults."""


class SourceEventPublisher:
    """Handles publication of source events."""

    def __init__(
        self, *, config: SourceEventPublisherConfig, provider: EventPublisherProtocol
    ):
        """Initialize with config parameters."""
        self._config = config
        self._provider = provider

    def publish_submission(self, submission: models.Submission):
        """Publish the current submission as source event"""
        if submission.content is None:
            raise ValueError("Submission content must be defined.")

        payload = SubmissionEventPayload(
            submission_id=submission.id,
            content=submission.content,
            annotation=SubmissionAnnotation(accession_map=submission.accession_map),
        )

        asyncio.run(
            self._provider.publish(
                topic=self._config.source_event_topic,
                type_=self._config.source_event_type,
                key=submission.id,
                payload=json.loads(payload.model_dump_json()),
            )
        )
