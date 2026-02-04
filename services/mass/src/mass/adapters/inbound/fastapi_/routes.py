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

"""API endpoints"""

import logging
from typing import Annotated

from fastapi import APIRouter, Query, status
from fastapi.exceptions import HTTPException

from mass.adapters.inbound.fastapi_.dummies import ConfigDummy, QueryHandlerDummy
from mass.core import models

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/health",
    summary="health",
    status_code=status.HTTP_200_OK,
)
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


@router.get(
    path="/search-options",
    summary="Retrieve all configured resource classes with their facetable and selected fields",
    response_model=dict[str, models.SearchableClass],
)
async def search_options(
    config: ConfigDummy,
) -> dict[str, models.SearchableClass]:
    """Return the configured searchable classes.

    The returned object describes which resource classes are accounted for in the system,
    as well as their facetable and selected fields.
    The facetable fields represent specific data fields that will be aggregated alongside
    the search hits for further search refinement.
    The selected fields are those that will appear in the search results.
    They contain a key, which is used by the system, and a name, which is more user-friendly.
    """
    return config.searchable_classes


@router.get(
    path="/search",
    summary="Perform a search using query string and filter parameters",
    response_model=models.QueryResults,
)
async def search(  # noqa: PLR0913
    query_handler: QueryHandlerDummy,
    class_name: Annotated[str, Query(description="The class name to search")],
    query: Annotated[str, Query(description="The keyword search for the query")] = "",
    filter_by: Annotated[
        list[str] | None,
        Query(description="Field(s) that shall be used for filtering results"),
    ] = None,
    value: Annotated[
        list[str] | None,
        Query(description="Values(s) that shall be used for filtering results"),
    ] = None,
    skip: Annotated[
        int, Query(description="The number of results to skip for pagination")
    ] = 0,
    limit: Annotated[
        int | None, Query(description="Limit the results to this number")
    ] = None,
    order_by: Annotated[
        list[str] | None,
        Query(description="Field(s) that shall be used for sorting results"),
    ] = None,
    sort: Annotated[
        list[models.SortOrder] | None,
        Query(description="Sort order(s) that shall be used when sorting results"),
    ] = None,
) -> models.QueryResults | None:
    """Perform search query"""
    if not class_name:
        raise HTTPException(status_code=422, detail="A class name must be specified")
    try:
        filters = [
            models.Filter(key=field, value=value)
            for field, value in zip(filter_by or [], value or [], strict=True)
        ]
    except ValueError as err:
        detail = "Number of fields to filter by must match number of values"
        raise HTTPException(status_code=422, detail=detail) from err
    if order_by and len(set(order_by)) < len(order_by):
        detail = "Fields to order by must be unique"
        raise HTTPException(status_code=422, detail=detail)
    try:
        sorting_parameters = [
            models.SortingParameter(field=field, order=order)
            for field, order in zip(order_by or [], sort or [], strict=True)
        ]
    except ValueError as err:
        detail = "Number of fields to order by must match number of sort options"
        raise HTTPException(status_code=422, detail=detail) from err
    try:
        results = await query_handler.handle_query(
            class_name=class_name,
            query=query,
            filters=filters,
            skip=skip,
            limit=limit,
            sorting_parameters=sorting_parameters,
        )
    except query_handler.ClassNotConfiguredError as err:
        raise HTTPException(
            status_code=422,
            detail="The specified class name is invalid."
            + " See /search-options for a list of valid class names.",
        ) from err
    except (query_handler.SearchError, query_handler.ValidationError) as err:
        log.error(err, exc_info=True)
        raise HTTPException(
            status_code=500, detail="An error occurred during the search operation"
        ) from err

    return results
