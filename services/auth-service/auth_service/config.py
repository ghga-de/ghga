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

import logging.config
from typing import Any, Literal, Optional

from ghga_service_commons.api import ApiConfigBase, LogLevel
from ghga_service_commons.auth.ghga import AuthConfig
from hexkit.config import config_from_yaml
from pydantic import HttpUrl, SecretStr


def configure_logging():
    """Configure the application logging.

    This must happen before the application is configured.
    """
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "()": "uvicorn.logging.DefaultFormatter",
                    "fmt": "%(levelprefix)s %(asctime)s %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                },
            },
            "loggers": {
                "auth_service": {
                    "handlers": ["default"],
                    "level": CONFIG.log_level.upper(),
                },
            },
        }
    )


@config_from_yaml(prefix="auth_service")
class Config(ApiConfigBase, AuthConfig):
    """Config parameters and their defaults."""

    service_name: str = "auth_service"
    log_level: LogLevel = "debug"

    run_auth_adapter: bool = False

    # external API path for the user management as seen by the auth adapter
    api_ext_path: str = "/api/auth"

    # internal public key for user management (key pair for auth adapter)
    auth_key: Optional[str] = None
    # allowed algorithms for signing internal tokens
    auth_algs: list[str] = ["ES256"]
    # internal claims that shall be verified
    auth_check_claims: dict[str, Any] = dict.fromkeys("name email iat exp".split())
    # mapping of claims to the internal auth context
    auth_map_claims: dict[str, str] = {}
    # external public key set for auth adapter (not used for user management)
    auth_ext_keys: Optional[str] = None
    # allowed algorithms for signing external tokens
    auth_ext_algs: list[str] = ["RS256", "ES256"]
    # user(s) and password(s) for basic authentication
    basic_auth_user: Optional[str] = None
    # password(s) for basic authentication if not specified above
    basic_auth_pwd: Optional[str] = None
    # realm for basic authentication
    basic_auth_realm: str = "GHGA Data Portal"

    # if not run as auth adapter, which APIs should be provided
    include_apis: list[Literal["users", "claims"]] = ["users"]
    # a list of external IDs of data stewards to seed the claims repository with
    add_as_data_stewards: list[str] = []

    # expected external token content for validation in auth adapter
    oidc_authority_url: HttpUrl = "https://proxy.aai.lifescience-ri.eu"  # type: ignore
    oidc_userinfo_endpoint: Optional[HttpUrl] = (
        oidc_authority_url + "/OIDC/userinfo"  # type: ignore
    )
    oidc_client_id: str = "ghga-data-portal"

    # the URL used as source for internal claims
    organization_url: HttpUrl = "https://ghga.de"  # type: ignore

    db_url: SecretStr = "mongodb://mongodb:27017"  # type: ignore
    db_name: str = "user-management"
    users_collection: str = "users"
    claims_collection: str = "claims"


CONFIG = Config()  # pyright: ignore
