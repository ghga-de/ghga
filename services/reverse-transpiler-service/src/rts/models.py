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

"""Model definitions for the RTS"""

from typing import Any

from pydantic import BaseModel, Field


class Metadata(BaseModel):
    """A model representing a Metadata Artifact, identified by the study accession."""

    study_id: str = Field(
        ..., description="The ID of the study found within the metadata submission."
    )

    content: dict[str, Any] = Field(
        ...,
        description="The entire metadata content of the artifact.",
    )
