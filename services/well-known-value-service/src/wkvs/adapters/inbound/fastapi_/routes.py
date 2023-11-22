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

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException

from wkvs.adapters.inbound.fastapi_ import dummies
from wkvs.config import WellKnownConfig

WELLKNOWNS_FILTER: set[str] = WellKnownConfig.model_json_schema()["properties"].keys()

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
async def retrieve_value(
    value_name: str,
    config: dummies.ConfigDummy,
) -> dict[str, Any]:
    """Retrieves the given value from configuration
    Args:
        value_name: the name of the value to be retrieved

    Raises:
        HTTPException 404 when the specified value is not configured
    """
    try:
        available_values = config.model_dump(include=WELLKNOWNS_FILTER)
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
async def retrieve_all_values(
    config: dummies.ConfigDummy,
) -> dict[str, Any]:
    """Retrieves all values from the WellKnownsConfig class"""
    return config.model_dump(include=WELLKNOWNS_FILTER)
