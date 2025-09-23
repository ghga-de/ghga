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

from typing import Any

from ghga_service_commons.auth.ghga import AuthConfig
from ghga_service_commons.utils.multinode_storage import S3ObjectStoragesConfig
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from hexkit.opentelemetry import OpenTelemetryConfig
from hexkit.providers.akafka import KafkaConfig
from hexkit.providers.mongodb.migrations import MigrationConfig
from pydantic import Field

from dcs.adapters.inbound.event_sub import EventSubTranslatorConfig
from dcs.adapters.inbound.fastapi_.configure import DrsApiConfig
from dcs.adapters.outbound.event_pub import EventPubTranslatorConfig
from dcs.constants import SERVICE_NAME
from dcs.core.data_repository import DataRepositoryConfig


class WorkOrderTokenConfig(AuthConfig):
    """Overwrite checked claims"""

    auth_check_claims: dict[str, Any] = Field(
        default=dict.fromkeys(
            "type file_id user_public_crypt4gh_key iat exp".split()  # noqa: SIM905
        ),
        description="A dict of all GHGA internal claims that shall be verified.",
    )


@config_from_yaml(prefix=SERVICE_NAME)
class Config(
    DrsApiConfig,
    WorkOrderTokenConfig,
    DataRepositoryConfig,
    MigrationConfig,
    KafkaConfig,
    EventPubTranslatorConfig,
    EventSubTranslatorConfig,
    S3ObjectStoragesConfig,
    LoggingConfig,
    OpenTelemetryConfig,
):
    """Config parameters and their defaults."""

    service_name: str = SERVICE_NAME
