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

from typing import Literal

from ghga_service_commons.api import ApiConfigBase
from ghga_service_commons.auth.ghga import AuthConfig
from hexkit.config import config_from_yaml
from hexkit.log import LoggingConfig
from hexkit.opentelemetry import OpenTelemetryConfig
from hexkit.providers.akafka import KafkaConfig
from hexkit.providers.mongodb import MongoDbConfig
from hexkit.providers.mongokafka import MongoKafkaConfig
from pydantic import AnyUrl, Field, HttpUrl, field_validator

from auth_service.auth_adapter.core.session_store import SessionConfig
from auth_service.auth_adapter.core.totp import TOTPConfig
from auth_service.claims_repository.models.config import UserWithIVA
from auth_service.claims_repository.translators.dao import (
    ClaimDaoConfig,
)
from auth_service.claims_repository.translators.event_sub import (
    EventSubTranslatorConfig,
)
from auth_service.user_registry.core.registry import UserRegistryConfig
from auth_service.user_registry.translators.dao import UserDaoConfig
from auth_service.user_registry.translators.event_pub import (
    EventPubTranslatorConfig,
)

SERVICE_NAME = "auth_service"


@config_from_yaml(prefix=SERVICE_NAME)
class Config(
    ApiConfigBase,
    AuthConfig,
    SessionConfig,
    TOTPConfig,
    UserRegistryConfig,
    LoggingConfig,
    MongoKafkaConfig,
    MongoDbConfig,
    KafkaConfig,
    UserDaoConfig,
    ClaimDaoConfig,
    EventSubTranslatorConfig,
    EventPubTranslatorConfig,
    OpenTelemetryConfig,
):
    """Config parameters and their defaults."""

    service_name: str = Field(
        default=SERVICE_NAME, description="Short name of this service"
    )

    auth_key: str | None = Field(  # type: ignore
        default=None,
        description="internal public key for the auth service"
        " (key pair for auth adapter)",
    )

    api_ext_path: str = Field(
        default="/api/auth",
        description="external API path for the auth related endpoints"
        " (user, session and TOTP management)",
    )

    auth_ext_keys: str | None = Field(
        default=None,
        description="external public key set for auth adapter"
        " (used only by the auth adapter, determined using OIDC discovery if None)",
    )
    auth_ext_algs: list[str] = Field(
        default=["RS256", "ES256"],
        description="allowed algorithms for signing external tokens",
    )

    auth_paths: list[str] = Field(
        default=["/api/"],
        description="path prefixes that can generate an internal auth token",
    )

    basic_auth_credentials: str | None = Field(
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

    provide_apis: list[Literal["ext_auth", "users", "claims", "access"]] = Field(
        default=[],
        description="Which REST APIs should be provided.",
        title="Provide APIs",
        examples=['["ext_auth"]', '["users"]', '["claims", "access"]'],
    )

    run_consumer: bool = Field(
        default=False,
        description="Whether the service should run as an event consumer",
        examples=["false", "true"],
    )

    add_as_data_stewards: list[UserWithIVA] = Field(
        default=[],
        description="A list of of data stewards to seed the claims repository with."
        " All other data steward claims will be removed."
        " This is only used with the claims API.",
    )

    oidc_authority_url: HttpUrl = Field(
        default="https://login.aai.lifescience-ri.eu/oidc/",
        description="external OIDC authority URL used by the auth adapter",
    )  # type: ignore
    oidc_issuer: str = Field(
        default="https://login.aai.lifescience-ri.eu/oidc/",
        description="external OIDC issuer for access tokens used by the auth adapter"
        " (URL format with or without end slash, determined using OIDC discovery if empty)",
    )
    oidc_userinfo_endpoint: HttpUrl | None = Field(
        default="https://login.aai.lifescience-ri.eu/oidc/userinfo",
        description="external OIDC userinfo endpoint used by the auth adapter"
        " (determined using OIDC discovery if None)",
    )  # type: ignore
    oidc_client_id: str = Field(
        default="ghga-data-portal", description="the registered OIDC client ID"
    )

    organization_url: HttpUrl = Field(
        default="https://ghga.de",
        description="the URL used as source for internal claims",
    )  # type: ignore

    db_name: str = Field(
        default="auth-db",
        examples=["auth-db", "user-management", "users-and-claims"],
        description="the name of the database located on the MongoDB server",
    )

    dataset_change_topic: str = Field(
        default="metadata_datasets",
        description="the topic of the event announcing dataset deletions",
    )
    dataset_deletion_type: str = Field(
        default="dataset_deleted",
        description="the type of the event announcing dataset deletions",
    )
    dataset_upsertion_type: str = Field(  # required, but unused
        default="dataset_created",
        description="the type of the event announcing dataset upsertions",
    )

    @field_validator("oidc_issuer")
    @classmethod
    def check_http_url(cls, v: str) -> str:
        """Make sure the string is a valid URL if specified."""
        if v:
            url = AnyUrl(url=v)
            if url.scheme not in ("http", "https"):
                raise ValueError(f"Invalid URL scheme: {url.scheme}")
        return v


CONFIG = Config()  # type: ignore


def get_config() -> Config:
    """Get runtime configuration."""
    return CONFIG
