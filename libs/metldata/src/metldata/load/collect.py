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

"""Functionality for collecting available artifacts."""

from collections import defaultdict
from typing import cast

from pydantic import Field, field_validator

from metldata.custom_types import Json
from metldata.event_handling.artifact_events import (
    ArtifactEventConfig,
    get_artifact_topic,
)
from metldata.event_handling.event_handling import FileSystemEventCollector
from metldata.load.models import ArtifactJson, ArtifactResourceDict


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

    # This config value is also defined in ArtifactLoaderAPIConfig
    publishable_artifacts: list[str] = Field(
        default_factory=list,
        description="List of artifacts to be published in their entirety when loaded"
        " into the Loader API.",
        examples=[[], ["added_accessions"]],
    )

    @field_validator("artifact_types")
    def artifact_types_must_not_contain_dots(cls, value: list[str]):  # noqa: N805
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
            content = cast(Json, event.payload.get("content"))
            if not content:
                raise RuntimeError("Artifact does not contain 'content' field.")

            # Most loaded data will have blank study_accession. Only publishable
            # artifacts will have a study_accession. This is a temporary workaround
            # to avoid over-complicating accounting for the different structure of
            # the stats_public artifact. Eventually, new services will make this all
            # obsolete.
            study_accession = ""
            if artifact_type in config.publishable_artifacts:
                # If the artifact is publishable, we expect it to have a study_accession
                # field. This is checked here to avoid encountering an error later
                # on when the uploaded data is already half-way processed.
                try:
                    study_accession = content["studies"][0]["accession"]
                except (KeyError, IndexError) as err:
                    raise RuntimeError(
                        f"Artifact '{artifact_type}' does not contain 'study_accession'"
                        " field, but it is marked as publishable."
                    ) from err

            artifact_resources[artifact_type].append(
                ArtifactJson(
                    artifact_name=artifact_type,
                    study_accession=study_accession,
                    content=content,
                )
            )

    return artifact_resources
