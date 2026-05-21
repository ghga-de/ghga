# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from hexkit.opentelemetry import OpenTelemetryConfig
from hexkit.providers.mongodb.migrations import MigrationConfig
from hexkit.providers.mongokafka import MongoKafkaConfig
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from pydantic import Field, field_validator

from fis.adapters.inbound.event_sub import OutboxSubConfig
from fis.adapters.outbound.event_pub import EventPubConfig
from fis.adapters.outbound.http import HttpClientConfig
from fis.adapters.outbound.secrets import SecretsClientConfig
from fis.constants import SERVICE_NAME


@config_from_yaml(prefix=SERVICE_NAME)
class Config(
    MongoKafkaConfig,
    MigrationConfig,
    ApiConfigBase,
    EventPubConfig,
    LoggingConfig,
    OpenTelemetryConfig,
    OutboxSubConfig,
    SecretsClientConfig,
    HttpClientConfig,
):
    """Config parameters and their defaults."""

    service_name: str = SERVICE_NAME

    data_hub_auth_keys: dict[str, str] = Field(
        default=...,
        description=(
            "Mapping of storage (data hub) aliases to their public token signature"
            + " validation keys"
        ),
        examples=[
            {
                "HD": '{"crv": "P-256", "kty": "EC", "x": "...", "y": "..."}',
                "TU": '{"crv": "P-256", "kty": "EC", "x": "...", "y": "..."}',
            }
        ],
    )

    dhfs_version_constraint: str = Field(
        default=...,
        description=(
            "A PEP 440 version specifier controlling which DHFS client versions are"
            + " accepted. Requests where the reported version does not satisfy this"
            + " specifier will be rejected with a 426 error."
        ),
        examples=[">=1.0.0,<2.0.0", "~=2.0"],
    )

    @field_validator("dhfs_version_constraint")
    @classmethod
    def validate_dhfs_version_constraint(cls, value: str) -> str:
        """Ensure dhfs_version_constraint is a valid PEP 440 version specifier."""
        try:
            SpecifierSet(value)
        except InvalidSpecifier as err:
            raise ValueError(
                f"Invalid version specifier for dhfs_version_constraint: {err}"
            ) from err
        return value
