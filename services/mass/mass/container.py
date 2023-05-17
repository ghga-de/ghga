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
#
"""Dependency-Injection container"""
from hexkit.inject import ContainerBase, get_configurator, get_constructor
from hexkit.providers.mongodb.provider import MongoDbDaoFactory

from mass.adapters.outbound.aggregator import AggregatorCollection, AggregatorFactory
from mass.adapters.outbound.dao import DaoCollection
from mass.config import Config
from mass.core.query_handler import QueryHandler


class Container(ContainerBase):
    """Dependency-Injection Container"""

    config = get_configurator(Config)
    dao_factory = get_constructor(MongoDbDaoFactory, config=config)
    aggregator_factory = get_constructor(AggregatorFactory, config=config)

    dao_collection = get_constructor(
        DaoCollection, dao_factory=dao_factory, config=config
    )

    aggregator_collection = get_constructor(
        AggregatorCollection, aggregator_factory=aggregator_factory, config=config
    )

    query_handler = get_constructor(
        QueryHandler,
        config=config,
        dao_collection=dao_collection,
        aggregator_collection=aggregator_collection,
    )
