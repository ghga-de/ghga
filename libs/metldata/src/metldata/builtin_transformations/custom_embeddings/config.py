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

"""Models used to describe embedding profiles."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from metldata.builtin_transformations.custom_embeddings.embedding_profile import (
    EmbeddingProfile,
)


def _get_target_class_names(*, embedding_profile: EmbeddingProfile) -> list[str]:
    """A function to get the names of the target classes from an embedding profile
    including nested embedding profiles.
    """
    embedded_classes = [embedding_profile.target_class]
    for referenced_profile in embedding_profile.embedded_references.values():
        if isinstance(referenced_profile, EmbeddingProfile):
            embedded_classes.extend(
                _get_target_class_names(embedding_profile=referenced_profile)
            )

    return embedded_classes


class CustomEmbeddingConfig(BaseSettings):
    """Config to describe profiles for custom embeddings of classes from a metadata
    model.
    """

    model_config = SettingsConfigDict(extra="forbid")

    embedding_profiles: list[EmbeddingProfile] = Field(
        ...,
        description=(
            "A list of custom embedding profiles for classes from a metadata model."
        ),
    )

    # pylint: disable=no-self-argument
    @field_validator("embedding_profiles")
    def check_embedding_profiles_unique(
        cls,
        value: list[EmbeddingProfile],
    ) -> list[EmbeddingProfile]:
        """Check that names for embedded classes are unique among the embedding_profiles."""
        embedded_classes = [
            embedded_class
            for profile in value
            for embedded_class in _get_target_class_names(embedding_profile=profile)
        ]

        if len(embedded_classes) != len(set(embedded_classes)):
            raise ValueError("Names for embedded classes must be unique.")

        return value
