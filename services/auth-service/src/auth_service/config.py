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

"""Config Parameter Modeling and Parsing"""

from typing import Literal, Optional, Union

from ghga_service_commons.api import ApiConfigBase
from ghga_service_commons.auth.ghga import AuthConfig
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from hexkit.providers.akafka import KafkaConfig
from hexkit.providers.mongodb import MongoDbConfig
from pydantic import Field, HttpUrl

from auth_service.auth_adapter.core.session_store import SessionConfig
from auth_service.auth_adapter.core.totp import TOTPConfig
from auth_service.user_management.claims_repository.translators.akafka import (
    EventSubTranslatorConfig,
)
from auth_service.user_management.claims_repository.translators.dao import (
    ClaimDaoConfig,
)
from auth_service.user_management.user_registry.core.registry import UserRegistryConfig
from auth_service.user_management.user_registry.translators.dao import UserDaoConfig

SERVICE_NAME = "auth_service"


@config_from_yaml(prefix=SERVICE_NAME)
class Config(
    ApiConfigBase,
    AuthConfig,
    SessionConfig,
    TOTPConfig,
    UserRegistryConfig,
    LoggingConfig,
    MongoDbConfig,
    UserDaoConfig,
    ClaimDaoConfig,
    KafkaConfig,
    EventSubTranslatorConfig,
):
    """Config parameters and their defaults."""

    service_name: str = Field(
        default=SERVICE_NAME, description="Short name of this service"
    )

    run_auth_adapter: bool = Field(default=False, description="Run as auth adapter")

    auth_key: Optional[str] = Field(
        default=None,
        description="internal public key for user management"
        " (key pair for auth adapter)",
    )

    api_ext_path: str = Field(
        default="/api/auth",
        description="external API path for the auth related endpoints"
        " (user, session and TOTP management)",
    )

    auth_ext_keys: Optional[str] = Field(
        default=None,
        description="external public key set for auth adapter"
        " (not used for user management)",
    )
    auth_ext_algs: list[str] = Field(
        default=["RS256", "ES256"],
        description="allowed algorithms for signing external tokens",
    )

    basic_auth_credentials: Optional[str] = Field(
        default=None,
        description="credentials for basic authentication, separated by whitespace",
    )
    basic_auth_realm: str = Field(
        default="GHGA Data Portal", description="realm for basic authentication"
    )

    allow_read_paths: list[str] = Field(
        default=["/.well-known/*", "/service-logo.png"],
        description="paths that are public or use their own authentication mechanism",
    )
    allow_write_paths: list[str] = Field(
        default=[],
        description="paths for writing that use their own authentication mechanism",
    )

    include_apis: list[Literal["users", "claims"]] = Field(
        default=["users"],
        description="If not run as auth adapter, which APIs should be provided."
        " If no APIs are specified, run the event consumer.",
    )

    add_as_data_stewards: list[Union[str, dict]] = Field(
        default=[],
        description="a list of external IDs of data stewards or user objects"
        " to seed the claims repository with",
    )

    oidc_authority_url: HttpUrl = Field(
        default="https://proxy.aai.lifescience-ri.eu",
        description="external OIDC authority URL used by the auth adapter",
    )
    oidc_userinfo_endpoint: Optional[HttpUrl] = Field(
        default="https://proxy.aai.lifescience-ri.eu/OIDC/userinfo",
        description="external OIDC userinfo endpoint used by the auth adapter",
    )
    oidc_client_id: str = Field(
        default="ghga-data-portal", description="the registered OIDC client ID"
    )

    organization_url: HttpUrl = Field(
        default="https://ghga.de",
        description="the URL used as source for internal claims",
    )

    db_name: str = Field(
        default="auth-db",
        examples=["auth-db", "user-management", "users-and-claims"],
        description="the name of the database located on the MongoDB server",
    )

    dataset_deletion_event_topic: str = Field(
        default="metadata_datasets",
        description="the topic of the event announcing dataset deletions",
    )
    dataset_deletion_event_type: str = Field(
        default="dataset_deleted",
        description="the type of the event announcing dataset deletions",
    )


CONFIG = Config()  # pyright: ignore
