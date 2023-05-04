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
from hexkit.providers.mongodb import MongoDbConfig
from pydantic import Field

from metldata.artifacts_rest.config import ArtifactsRestConfig


class ArtifactLoaderAPIConfig(ArtifactsRestConfig, ApiConfigBase, MongoDbConfig):
    """Config settings and their defaults."""

    loader_token_hashes: list[str] = Field(
        ..., description="Hashes of tokens used to authenticate for loading artifact."
    )
