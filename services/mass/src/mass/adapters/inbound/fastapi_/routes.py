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

"""API endpoints"""

import logging
from typing import Union

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException

from mass.adapters.inbound.fastapi_ import models as api_models
from mass.config import Config
from mass.container import Container
from mass.core import models
from mass.ports.inbound.query_handler import QueryHandlerPort

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


# GET /rpc/search-options
@router.get(
    path="/rpc/search-options",
    summary="Retrieve all configured resource classes and facetable properties",
    response_model=dict[str, models.SearchableClass],
)
@inject
async def search_options(
    config: Config = Depends(Provide[Container.config]),
) -> dict[str, models.SearchableClass]:
    """Returns the configured searchable classes. This describes which resource classes
    are accounted for in the system, as well as their facetable properties. The facetable
    properties represent specific data properties that will be aggregated alongside the
    search hits for further search refinement. They contain a key, which is used by the
    system, and a name, which is more user-friendly.
    """
    return config.searchable_classes


# POST /rpc/search
@router.post(
    path="/rpc/search",
    summary="Perform a search using query string and filter parameters",
    response_model=models.QueryResults,
)
@inject
async def search(
    parameters: api_models.SearchParameters,
    query_handler: QueryHandlerPort = Depends(Provide[Container.query_handler]),
) -> Union[models.QueryResults, None]:
    """Perform search query"""
    try:
        results = await query_handler.handle_query(
            class_name=parameters.class_name,
            query=parameters.query,
            filters=parameters.filters,
            skip=parameters.skip,
            limit=parameters.limit,
            sorting_parameters=parameters.sorting_parameters,
        )
    except query_handler.ClassNotConfiguredError as err:
        raise HTTPException(
            status_code=422,
            detail="The specified class name is invalid."
            + " See /rpc/search-options for a list of valid class names.",
        ) from err
    except (query_handler.SearchError, query_handler.ValidationError) as err:
        log.error("Search operation error: %s", err)
        raise HTTPException(
            status_code=500, detail="An error occurred during search operation"
        ) from err

    return results
