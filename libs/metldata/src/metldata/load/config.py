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

from ghga_service_commons.api import ApiConfigBase
from hexkit.providers.akafka import KafkaConfig
from hexkit.providers.mongodb import MongoDbConfig
from pydantic import Field

from metldata.artifacts_rest.config import ArtifactsRestConfig
from metldata.event_handling.event_handling import FileSystemEventConfig
from metldata.load.collect import ArtifactCollectorConfig
from metldata.load.event_publisher import EventPubTranslatorConfig


class ArtifactLoaderAPIConfig(  # pylint: disable=too-many-ancestors
    ArtifactsRestConfig,
    ApiConfigBase,
    EventPubTranslatorConfig,
    KafkaConfig,
    MongoDbConfig,
):
    """Config settings for the loader API."""

    loader_token_hashes: list[str] = Field(
        ..., description="Hashes of tokens used to authenticate for loading artifact."
    )


class ArtifactLoaderClientConfig(ArtifactCollectorConfig, FileSystemEventConfig):
    """Config settings for the loader client."""

    loader_api_root: str = Field(..., description="Root URL of the loader API.")
