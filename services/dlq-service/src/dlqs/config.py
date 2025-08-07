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

"""Config Parameter Modeling and Parsing."""

from ghga_service_commons.api import ApiConfigBase
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from hexkit.providers.akafka.config import KafkaConfig
from hexkit.providers.mongodb.migrations import MigrationConfig
from pydantic import Field

SERVICE_NAME: str = "dlqs"


@config_from_yaml(prefix=SERVICE_NAME)
class Config(ApiConfigBase, LoggingConfig, KafkaConfig, MigrationConfig):
    """Config parameters and their defaults."""

    service_name: str = Field(
        default=SERVICE_NAME, description="Short name of this service"
    )
    token_hashes: list[str] = Field(
        default=...,
        description="List of token hashes corresponding to the tokens that can be used "
        + "to authenticate calls to this service. Hashes are made with SHA-256.",
        examples=["7ad83b6b9183c91674eec897935bc154ba9ff9704f8be0840e77f476b5062b6e"],
    )


CONFIG = Config()  # type: ignore
