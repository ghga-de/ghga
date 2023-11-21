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

"""Functionality for collecting available artifacts."""

from collections import defaultdict

from pydantic import Field, field_validator

from metldata.event_handling.artifact_events import (
    ArtifactEventConfig,
    get_artifact_topic,
)
from metldata.event_handling.event_handling import FileSystemEventCollector
from metldata.load.models import ArtifactResourceDict


class ArtifactCollectorConfig(ArtifactEventConfig):
    """Config parameters and their defaults."""

    artifact_types: list[str] = Field(
        ...,
        description=(
            "The artifacts types of interest. Together with the topic prefix, they"
            + " determine the topics to subscribe to. The artifact types must not"
            + " contain dots."
        ),
    )

    @field_validator("artifact_types")
    def artifact_types_must_not_contain_dots(cls, value: list[str]):
        """Validate that artifact types do not contain dots."""
        for artifact_type in value:
            if "." in artifact_type:
                raise ValueError(
                    f"Artifact type '{artifact_type}' must not contain dots."
                )

        return value


def collect_artifacts(
    *, config: ArtifactCollectorConfig, event_collector: FileSystemEventCollector
) -> ArtifactResourceDict:
    """Collect artifacts from the file system."""
    artifact_resources: ArtifactResourceDict = defaultdict(list)
    for artifact_type in config.artifact_types:
        topic = get_artifact_topic(
            artifact_topic_prefix=config.artifact_topic_prefix,
            artifact_type=artifact_type,
        )
        for event in event_collector.collect_events(topic=topic):
            content = event.payload.get("content")
            if not content:
                raise RuntimeError("Artifact does not contain 'content' field.")
            artifact_resources[artifact_type].append(content)

    return artifact_resources
