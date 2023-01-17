# Copyright 2021 - 2023 Universität Tübingen, DKFZ and EMBL
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
from typing import Optional

from ghga_service_chassis_lib.api import ApiConfigBase, LogLevel
from ghga_service_chassis_lib.config import config_from_yaml


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
class Config(ApiConfigBase):
    """Config parameters and their defaults."""

    service_name: str = "auth_service"
    log_level: LogLevel = "debug"

    run_auth_adapter: bool = False

    # extermal API path for the user management as seen by the auth adapter
    api_ext_path: str = "/api/auth"

    # internal public key for user management (key pair for auth adapter)
    auth_int_keys: Optional[str] = None
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

    # expected external token content for validation in auth adapter
    oidc_authority_url: str = "https://proxy.aai.lifescience-ri.eu"
    oidc_client_id: str = "ghga-data-portal"

    # the URL used as source for internal claims
    organization_url: str = "https://ghga.de"

    db_url: str = "mongodb://localhost:27017"
    db_name: str = "user-management"
    users_collection: str = "users"
    claims_collection: str = "claims"


CONFIG = Config()
