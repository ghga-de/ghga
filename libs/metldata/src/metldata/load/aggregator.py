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

"""Protocol and provider for a database aggregator."""

from abc import abstractmethod
from typing import Any

from hexkit.protocols.dao import DaoFactoryProtocol
from hexkit.providers.mongodb import MongoDbDaoFactory


class DbAggregator(DaoFactoryProtocol):
    """A DaoFactory that can also aggregate."""

    @abstractmethod
    async def aggregate(
        self, *, collection_name: str, pipeline: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Run the given aggregation pipeline."""
        ...


class MongoDbAggregator(MongoDbDaoFactory, DbAggregator):
    """A MongoDB-based DaoFactory that can also aggregate."""

    async def aggregate(
        self, *, collection_name: str, pipeline: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Run the given aggregation pipeline."""
        collection = self._db[collection_name]
        return [item async for item in collection.aggregate(pipeline=pipeline)]
