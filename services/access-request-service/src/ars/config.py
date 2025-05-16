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

"""Config Parameter Modeling and Parsing"""

from ghga_service_commons.api import ApiConfigBase
from ghga_service_commons.auth.ghga import AuthConfig
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from hexkit.providers.mongodb.migrations import MigrationConfig
from hexkit.providers.mongokafka import MongoKafkaConfig
from pydantic import Field

from ars.adapters.inbound.event_sub import EventSubTranslatorConfig
from ars.adapters.outbound.daos import AccessRequestDaoConfig
from ars.adapters.outbound.http import AccessGrantsConfig
from ars.core.repository import AccessRequestConfig

SERVICE_NAME = "ars"


@config_from_yaml(prefix=SERVICE_NAME)
class Config(
    ApiConfigBase,
    AuthConfig,
    LoggingConfig,
    MigrationConfig,
    MongoKafkaConfig,
    EventSubTranslatorConfig,
    AccessRequestDaoConfig,
    AccessGrantsConfig,
    AccessRequestConfig,
):
    """Config parameters and their defaults."""

    service_name: str = Field(
        default=SERVICE_NAME, description="Short name of this service"
    )
