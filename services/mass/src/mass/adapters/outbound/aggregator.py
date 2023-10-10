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
"""Contains concrete implementation of the Aggregator and its Factory"""
from typing import Optional

from hexkit.custom_types import JsonObject
from hexkit.providers.mongodb.provider import MongoDbConfig
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import OperationFailure

from mass.adapters.outbound import utils
from mass.config import SearchableClassesConfig
from mass.core import models
from mass.ports.outbound.aggregator import (
    AggregationError,
    AggregatorCollectionPort,
    AggregatorPort,
)


class Aggregator(AggregatorPort):
    """Concrete implementation of an Aggregator"""

    def __init__(self, *, collection):
        """Initialize with a MongoDB collection"""
        self._collection = collection

    async def aggregate(  # noqa: PLR0913, D102
        self,
        *,
        query: str,
        filters: list[models.Filter],
        facet_fields: list[models.FacetLabel],
        skip: int = 0,
        limit: Optional[int] = None,
        sorting_parameters: list[models.SortingParameter],
    ) -> JsonObject:
        # don't carry out aggregation if the collection is empty
        if not await self._collection.find_one():
            return models.QueryResults().dict()

        # build the aggregation pipeline
        pipeline = utils.build_pipeline(
            query=query,
            filters=filters,
            facet_fields=facet_fields,
            skip=skip,
            limit=limit,
            sorting_parameters=sorting_parameters,
        )

        try:
            [results] = [
                item async for item in self._collection.aggregate(pipeline=pipeline)
            ]
        except OperationFailure as err:
            aggregation_details = (
                f"query={query}, "
                + "filters={[{filter_.key: filter_.value} for filter_ in filters]}, "
                + "facet_fields={facet_fields}, skip={skip}, limit={limit}"
                + ". Check that all documents have required facet fields."
            )
            raise AggregationError(aggregation_details=aggregation_details) from err

        return results


class AggregatorFactory:
    """Produces aggregators for a given resource class"""

    def __init__(self, *, config: MongoDbConfig):
        """Initialize the factory with the DB config information"""
        self._config = config
        self._client = AsyncIOMotorClient(
            self._config.db_connection_str.get_secret_value()
        )
        self._db = self._client[self._config.db_name]

    def get_aggregator(self, *, name: str) -> Aggregator:
        """Returns an aggregator with a collection set up"""
        collection = self._db[name]
        return Aggregator(collection=collection)


class AggregatorNotFoundError(RuntimeError):
    """Raised when an Aggregator is not found."""

    def __init__(self, class_name: str):
        super().__init__(f"Could not find Aggregator for class '{class_name}'.")


class AggregatorCollection(AggregatorCollectionPort):
    """Provides an Aggregator for each configured searchable resource class"""

    @classmethod
    async def construct(
        cls,
        aggregator_factory: AggregatorFactory,
        config: SearchableClassesConfig,
    ):
        """Initialize the Aggregator collection with one Aggregator for each resource class"""
        aggregators: dict[str, AggregatorPort] = {}
        for name in config.searchable_classes:
            aggregators[name] = aggregator_factory.get_aggregator(name=name)

        return cls(aggregators=aggregators)

    def __init__(
        self,
        aggregators: dict[str, AggregatorPort],
    ):
        """Initialize the collection of Aggregators"""
        self._aggregators = aggregators

    def get_aggregator(self, *, class_name: str) -> AggregatorPort:
        """Returns the aggregator for a given resource class name

        Raises:
            AggregatorNotFoundError: if the aggregator isn't found
        """
        try:
            return self._aggregators[class_name]
        except KeyError as err:
            raise AggregatorNotFoundError(class_name=class_name) from err
