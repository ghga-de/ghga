# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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
    # internal key pair for auth adapter, internal public key for user management
    auth_int_keys: Optional[str] = None
    # external public key set for auth adapter
    auth_ext_keys: Optional[str] = None
    # user(s) and password(s) for basic authentication
    basic_auth_user: Optional[str] = None
    # password(s) for basic authentication if not specified above
    basic_auth_pwd: Optional[str] = None
    # realm for basic authentication
    basic_auth_realm: Optional[str] = "GHGA Data Portal"
    db_url: str = "mongodb://localhost:27017"
    db_name: str = "user-registry"
    user_collection: str = "users"


CONFIG = Config()
