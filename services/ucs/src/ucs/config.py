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
from ghga_service_commons.utils.multinode_storage import S3ObjectStoragesConfig
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from hexkit.opentelemetry import OpenTelemetryConfig
from hexkit.providers.mongodb.migrations import MigrationConfig
from hexkit.providers.mongokafka import MongoKafkaConfig
from pydantic_settings import BaseSettings

from ucs.adapters.inbound.event_sub import EventSubConfig
from ucs.adapters.outbound.dao import UploadDaoConfig
from ucs.constants import SERVICE_NAME


class PublicKeyConfig(BaseSettings):
    """Auth config for WPS and UOS keys"""

    wps_auth_config: AuthConfig
    uos_auth_config: AuthConfig


@config_from_yaml(prefix=SERVICE_NAME)
class Config(
    ApiConfigBase,
    PublicKeyConfig,
    UploadDaoConfig,
    MongoKafkaConfig,
    MigrationConfig,
    S3ObjectStoragesConfig,
    LoggingConfig,
    OpenTelemetryConfig,
    EventSubConfig,
):
    """Config parameters and their defaults."""

    service_name: str = SERVICE_NAME
