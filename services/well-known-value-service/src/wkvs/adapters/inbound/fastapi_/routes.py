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
"""Contains endpoint functions for the API"""
from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException

from wkvs.config import WellKnownConfig
from wkvs.container import Container

WELLKNOWNS_FILTER: set[str] = WellKnownConfig.schema()["properties"].keys()

router = APIRouter()


@router.get(
    "/values/{value_name}",
    summary="retrieve a configured value",
    status_code=status.HTTP_200_OK,
    responses={
        "404": {
            "description": "Raised when a value is passed in for 'value_name' that is "
            + "not configured or otherwise available."
        }
    },
)
@inject
async def retrieve_value(
    value_name: str,
    config: WellKnownConfig = Depends(Provide[Container.config]),
) -> dict[str, Any]:
    """Retrieves the given value from configuration
    Args:
        value_name: the name of the value to be retrieved

    Raises:
        HTTPException 404 when the specified value is not configured
    """
    try:
        available_values = config.dict(include=WELLKNOWNS_FILTER)
        response = {value_name: available_values[value_name]}
    except KeyError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The value {value_name} is not configured",
        ) from err

    return response


@router.get(
    "/values",
    summary="retrieve all configured values",
    status_code=status.HTTP_200_OK,
)
@inject
async def retrieve_all_values(
    config: WellKnownConfig = Depends(Provide[Container.config]),
) -> dict[str, Any]:
    """Retrieves all values from the WellKnownsConfig class"""
    return config.dict(include=WELLKNOWNS_FILTER)
