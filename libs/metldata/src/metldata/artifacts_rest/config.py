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

"""Config parameters and their defaults."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from metldata.artifacts_rest.models import ArtifactInfo


class ArtifactsRestConfig(BaseSettings):
    """Config parameters and their defaults."""

    artifact_infos: list[ArtifactInfo] = Field(
        ...,
        description="Information for artifacts to be queryable via the Artifacts REST API.",
    )

    @field_validator("artifact_infos")
    def validate_artifact_info_names(
        cls, value: list[ArtifactInfo]
    ) -> list[ArtifactInfo]:
        """Validate that artifact names are unique."""
        artifact_names = [artifact_info.name for artifact_info in value]
        if len(artifact_names) != len(set(artifact_names)):
            raise ValueError("Artifact names must be unique.")

        return value
