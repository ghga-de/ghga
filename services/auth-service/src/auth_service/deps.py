# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from hexkit.providers.mongodb import MongoDbConfig, MongoDbDaoFactory
from hexkit.providers.mongokafka import MongoKafkaConfig, MongoKafkaDaoPublisherFactory

from .config import CONFIG, Config

__all__ = [
    "Config",
    "Depends",
    "get_config",
    "get_mongo_kafka_dao_factory",
    "get_mongodb_dao_factory",
]


def get_config() -> Config:
    """Get runtime configuration."""
    return CONFIG


def get_mongodb_dao_factory(
    config: Annotated[MongoDbConfig, Depends(get_config)],
) -> MongoDbDaoFactory:
    """Get a MongoDB DAO factory."""
    return MongoDbDaoFactory(config=config)


async def get_mongo_kafka_dao_factory(
    config: Annotated[MongoKafkaConfig, Depends(get_config)],
) -> AsyncGenerator[MongoKafkaDaoPublisherFactory, None]:
    """Get a MongoDB DAO publisher factory."""
    async with MongoKafkaDaoPublisherFactory.construct(config=config) as factory:
        yield factory
