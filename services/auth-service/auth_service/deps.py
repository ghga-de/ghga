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

"""FastAPI dependencies (used with the `Depends` feature)"""

from fastapi import Depends
from hexkit.providers.mongodb import MongoDbConfig, MongoDbDaoFactory

from .config import CONFIG, Config

__all__ = [
    "Depends",
    "get_config",
    "get_mongodb_config",
    "get_mongodb_dao_factory",
    "Config",
]


def get_config() -> Config:
    """Get runtime configuration."""
    return CONFIG


def get_mongodb_config(config: Config = Depends(get_config)) -> MongoDbConfig:
    """Get MongoDB configuration."""
    return MongoDbConfig(db_connection_str=config.db_url, db_name=config.db_name)


def get_mongodb_dao_factory(
    config: MongoDbConfig = Depends(get_mongodb_config),
) -> MongoDbDaoFactory:
    """Get MongoDB DAO factory."""
    return MongoDbDaoFactory(config=config)
