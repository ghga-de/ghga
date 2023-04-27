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

"""Logic for defining embedding profiles."""

from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel, Field


class EmbeddingProfile(BaseModel):
    """A model for describing a profile for embedding referenced classes into a class
    of interest of a metadata model. Please note, only the embedding for anchored
    classes that are referenced by this source class can be changed. All anchored
    classes are assumed to be non-embedded by default. The embedding profile can be used
    to define anchored classes as embedded given the slot named used for renferencing
    in the source class.
    """

    target_class: str = Field(
        ..., description="The name of the transformed class with embeddings."
    )
    source_class: str = Field(
        ..., description="The class to which the this embedding profile applies."
    )
    description: Optional[str] = Field(
        ..., description="Description of the transformed class with embeddings."
    )
    embedded_references: dict[str, Union[str, EmbeddingProfile]] = Field(
        ...,
        description=(
            "The references embedded into the target class."
            + "The keys are the names of slots in the target class that are used for "
            + " the references to other classes. The values are either the names of the"
            + " referenced classes or other embedding profiles if a custom embedding"
            + " will be applied to the referenced classes, too."
        ),
    )
