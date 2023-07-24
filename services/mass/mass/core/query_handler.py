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
"""Contains implementation of a QueryHandler to field queries on metadata"""
from typing import Optional

from hexkit.custom_types import JsonObject
from hexkit.providers.mongodb.provider import ResourceNotFoundError

from mass.config import SearchableClassesConfig
from mass.core import models
from mass.ports.inbound.query_handler import (
    ClassNotConfiguredError,
    DeletionFailedError,
    QueryHandlerPort,
    SearchError,
)
from mass.ports.outbound.aggregator import AggregationError, AggregatorCollectionPort
from mass.ports.outbound.dao import DaoCollectionPort


class QueryHandler(QueryHandlerPort):
    """Concrete implementation of a query handler"""

    def __init__(
        self,
        *,
        config: SearchableClassesConfig,
        aggregator_collection: AggregatorCollectionPort,
        dao_collection: DaoCollectionPort,
    ):
        """Initialize the query handler with resource daos/aggregators"""
        self._config = config
        self._aggregator_collection = aggregator_collection
        self._dao_collection = dao_collection

    async def load_resource(self, *, resource: models.Resource, class_name: str):
        """Helper function to load resources into the database"""
        dao = self._dao_collection.get_dao(class_name=class_name)
        await dao.upsert(resource)

    async def delete_resource(self, *, resource_id: str, class_name: str):
        if class_name not in self._config.searchable_classes:
            raise ClassNotConfiguredError(class_name=class_name)

        dao = self._dao_collection.get_dao(class_name=class_name)

        try:
            await dao.delete(id_=resource_id)
        except ResourceNotFoundError as err:
            raise DeletionFailedError(resource_id) from err

    async def handle_query(
        self,
        *,
        class_name: str,
        query: str,
        filters: list[models.Filter],
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> models.QueryResults:
        # get configured facet fields for given resource class
        try:
            facet_fields: list[models.FacetLabel] = self._config.searchable_classes[
                class_name
            ].facetable_properties
        except KeyError as err:
            raise ClassNotConfiguredError(class_name=class_name) from err

        # run the aggregation. Results will have {facets, count, hits} format
        aggregator = self._aggregator_collection.get_aggregator(class_name=class_name)
        try:
            aggregator_results: JsonObject = await aggregator.aggregate(
                query=query,
                filters=filters,
                facet_fields=facet_fields,
                skip=skip,
                limit=limit,
            )
        except AggregationError as exc:
            raise SearchError() from exc

        query_results = models.QueryResults(**aggregator_results)

        return query_results
