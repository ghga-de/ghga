# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

import logging

from pydantic import ValidationError

from hexkit.custom_types import JsonObject
from hexkit.protocols.dao import ResourceNotFoundError
from mass.config import SearchableClassesConfig
from mass.core import models
from mass.ports.inbound.query_handler import QueryHandlerPort
from mass.ports.outbound.aggregator import AggregationError, AggregatorCollectionPort
from mass.ports.outbound.dao import DaoCollectionPort

log = logging.getLogger(__name__)


class QueryHandler(QueryHandlerPort):
    """Concrete implementation of a query handler"""

    def __init__(
        self,
        *,
        config: SearchableClassesConfig,
        aggregator_collection: AggregatorCollectionPort,
        dao_collection: DaoCollectionPort,
    ):
        """Initialize the query handler with resource DAOs/aggregators"""
        self._config = config
        self._aggregator_collection = aggregator_collection
        self._dao_collection = dao_collection

    async def load_resource(  # noqa: D102
        self, *, resource: models.Resource, class_name: str
    ) -> None:
        if class_name not in self._config.searchable_classes:
            raise self.ClassNotConfiguredError(class_name=class_name)

        self._dao_collection.create_collections_and_indexes_if_needed()

        dao = self._dao_collection.get_dao(class_name=class_name)

        await dao.upsert(resource)

    async def delete_resource(self, *, resource_id: str, class_name: str) -> None:  # noqa: D102
        if class_name not in self._config.searchable_classes:
            raise self.ClassNotConfiguredError(class_name=class_name)

        dao = self._dao_collection.get_dao(class_name=class_name)

        try:
            await dao.delete(id_=resource_id)
        except ResourceNotFoundError as err:
            raise self.ResourceNotFoundError(resource_id=resource_id) from err

    def _complete_sort(self, sort: list[str] | None, *, query: str) -> list[str]:
        """Validate the sort specification and add the defaults to it.

        Raises:
            SortError: if a field is malformed or repeated, or if relevance is
                reversed or requested without a query.
        """
        sort = list(sort or [])
        fields = [spec.removeprefix("-") for spec in sort]
        for field in fields:
            # MongoDB rejects empty path components and those starting with a dollar
            if any(not part or part.startswith("$") for part in field.split(".")):
                raise self.SortError(f"Cannot sort by field '{field}'")
        if len(set(fields)) < len(fields):
            raise self.SortError("Fields to sort by must be unique")
        if f"-{models.RELEVANCE}" in sort:
            raise self.SortError("Sorting by relevance cannot be reversed")
        if models.RELEVANCE in sort and not query:
            raise self.SortError("Sorting by relevance requires a query")

        if not sort and query:
            sort.append(models.RELEVANCE)
        # the ID breaks ties, which keeps the order stable across pages
        if "id_" not in fields:
            sort.append("id_")
        return sort

    async def handle_query(  # noqa: D102, PLR0913
        self,
        *,
        class_name: str,
        query: str = "",
        filters: list[models.Filter] | None = None,
        sort: list[str] | None = None,
        skip: int = 0,
        limit: int | None = None,
    ) -> models.QueryResults:
        # a blank query is no query, so it must not imply sorting by relevance
        query = query.strip()

        sort = self._complete_sort(sort, query=query)

        if filters is None:
            filters = []

        # get configured facet and selected fields for given resource class
        try:
            searchable_class = self._config.searchable_classes[class_name]
            facet_fields: list[models.FieldLabel] = searchable_class.facetable_fields
            selected_fields: list[models.FieldLabel] = searchable_class.selected_fields
        except KeyError as err:
            raise self.ClassNotConfiguredError(class_name=class_name) from err

        # run the aggregation. Results will have {facets, items, total_count} format
        aggregator = self._aggregator_collection.get_aggregator(class_name=class_name)
        for attempt in range(2):
            try:
                aggregator_results: JsonObject = await aggregator.aggregate(
                    query=query,
                    filters=filters,
                    facet_fields=facet_fields,
                    selected_fields=selected_fields,
                    skip=skip,
                    limit=limit,
                    sort=sort,
                )
            except AggregationError as err:
                if err.missing_index and not attempt:
                    log.warning("Missing text indexes, trying to recreate them.")
                    try:
                        self._dao_collection.recreate_collections_and_indexes()
                    except Exception as recreation_error:
                        log.error("Cannot recreate text indexes: %s", recreation_error)
                        raise self.SearchError() from recreation_error
                    continue
                log.error("Search operation error: %s", err)
                raise self.SearchError() from err
            break

        try:
            query_results = models.QueryResults(**aggregator_results)
        except ValidationError as err:
            log.warning("Search results validation error: %s", err)
            raise self.ValidationError() from err

        return query_results
