# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Config classes for stateful events"""

from pydantic import Field
from pydantic_settings import BaseSettings

__all__ = [
    "DatasetEventsConfig",
    "ResourceEventsConfig",
    "UserEventsConfig",
]


class DatasetEventsConfig(BaseSettings):
    """For dataset change events."""

    dataset_change_topic: str = Field(
        ...,
        description="Name of the topic announcing, among other things, the list of"
        + " files included in a new dataset.",
        examples=["metadata_datasets"],
    )
    dataset_deletion_type: str = Field(
        ...,
        description="Type used for events announcing a new dataset overview.",
        examples=["dataset_deleted"],
    )
    dataset_upsertion_type: str = Field(
        ...,
        description="Type used for events announcing a new dataset overview.",
        examples=["dataset_created"],
    )


class ResourceEventsConfig(BaseSettings):
    """For searchable metadata resource change events."""

    resource_change_topic: str = Field(
        ...,
        description="Name of the topic used for events informing other services about"
        + " resource changes, i.e. deletion or insertion.",
        examples=["searchable_resources"],
    )
    resource_deletion_type: str = Field(
        ...,
        description="Type used for events indicating the deletion of a previously"
        + " existing resource.",
        examples=["searchable_resource_deleted"],
    )
    resource_upsertion_type: str = Field(
        ...,
        description="Type used for events indicating the upsert of a resource.",
        examples=["searchable_resource_upserted"],
    )


class UserEventsConfig(BaseSettings):
    """Config for communication changes to user data, done via outbox.

    The upsertion and deletion event types are hardcoded by `hexkit`.
    """

    user_topic: str = Field(
        default="users",
        description="The name of the topic containing user events.",
    )
