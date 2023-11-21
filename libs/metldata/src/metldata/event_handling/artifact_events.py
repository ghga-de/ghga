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

"""Logic for handling artifact events."""

from pydantic import BaseModel, Field, field_validator


class ArtifactEventConfig(BaseModel):
    """Config parameters and their defaults."""

    artifact_topic_prefix: str = Field(
        ...,
        description=(
            "The prefix used for topics containing artifacts. The topic name is"
            + " expected to be '{prefix}.{artifact_type}'. The prefix must not contain"
            + " dots."
        ),
    )

    @field_validator("artifact_topic_prefix")
    def artifact_topic_prefix_must_not_contain_dots(cls, value: str):
        """Validate that artifact topic prefix does not contain dots."""
        if "." in value:
            raise ValueError(f"Artifact topic prefix '{value}' must not contain dots.")

        return value


def get_artifact_topic(*, artifact_topic_prefix: str, artifact_type: str) -> str:
    """Get the topic name for the given artifact type.
    Both the provided artifact_topic_prefix and the artifact_type must not contain dots.
    """
    if "." in artifact_topic_prefix:
        raise ValueError(
            f"Artifact topic prefix '{artifact_topic_prefix}' must not contain dots."
        )
    if "." in artifact_type:
        raise ValueError(f"Artifact type '{artifact_type}' must not contain dots.")

    return f"{artifact_topic_prefix}.{artifact_type}"
