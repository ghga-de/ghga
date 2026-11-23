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
        int,
        Query(
            ge=0,
            le=2**63 - 1,  # MongoDB cannot encode larger ints
            description="The number of results to skip for pagination",
        ),
    ] = 0,
    limit: Annotated[
        int,
        Query(
            ge=0,
            le=1000,
            description="The maximum number of results to return,"
            + " where 0 returns only the facets and the total count",
        ),
    ] = 100,
    sort: Annotated[
        str | None,
        Query(
            description="A comma-separated list of field names defining the sort"
            + " order, where field names prefixed with '-' indicate descending order"
            + " (e.g. 'type,-title'). The reserved name 'relevance' sorts by how well"
            + " the results match the query, best first."
            + " Defaults to sorting by relevance if a query is given."
            + " If 'id_' is not referenced, it is appended as an ascending"
            + " tiebreaker to guarantee a stable order."
        ),
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
    try:
        results = await query_handler.handle_query(
            class_name=class_name,
            query=query,
            filters=filters,
            skip=skip,
            limit=limit,
            sort=[spec.strip() for spec in sort.split(",")] if sort else None,
        )
    except query_handler.ClassNotConfiguredError as err:
        raise HTTPException(
            status_code=422,
            detail="The specified class name is invalid."
            + " See /search-options for a list of valid class names.",
        ) from err
    except query_handler.SortError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    except (query_handler.SearchError, query_handler.ValidationError) as err:
        log.error(err, exc_info=True)
        raise HTTPException(
            status_code=500, detail="An error occurred during the search operation"
        ) from err

    return results
