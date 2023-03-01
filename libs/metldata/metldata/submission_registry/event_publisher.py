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

from pathlib import Path

from pydantic import BaseSettings, Field

from metldata.submission_registry import models
from metldata.submission_registry.utils import save_submission_as_json


class EventPublisherConfig(BaseSettings):
    """Config parameters and their defaults."""

    source_events_dir: Path = Field(
        ..., description="The directory where source events will be stored as JSON."
    )


def get_source_event_path(*, submission_id: str, source_events_dir: Path) -> Path:
    """Get the path for a source event."""

    return source_events_dir / f"{submission_id}.json"


class EventPublisher:
    """Handles publication of source events."""

    def __init__(
        self,
        *,
        config: EventPublisherConfig,
    ):
        """Initialize with config parameters."""

        self._config = config

    def publish_submission(self, submission: models.Submission):
        """Publish the current submission as source event"""

        if submission.content is None:
            raise ValueError("Submission content must be defined.")

        json_path = get_source_event_path(
            submission_id=submission.id,
            source_events_dir=self._config.source_events_dir,
        )
        save_submission_as_json(submission=submission, json_path=json_path)
