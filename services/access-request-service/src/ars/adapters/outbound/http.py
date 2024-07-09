# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Outbound HTTP calls"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings

from ars.ports.outbound.access_grants import AccessGrantsPort

__all__ = ["AccessGrantsConfig", "AccessGrantsAdapter"]

TIMEOUT = 60


class ClaimValidity(BaseModel):
    """Start and end dates for validating claims."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    valid_from: UTCDatetime = Field(
        ..., description="Start date of validity", examples=["2023-01-01T00:00:00Z"]
    )
    valid_until: UTCDatetime = Field(
        ..., description="End date of validity", examples=["2023-12-31T23:59:59Z"]
    )

    @model_validator(mode="after")
    def period_is_valid(self):
        """Validate that the dates of the period are in the right order."""
        if self.valid_until <= self.valid_from:
            raise ValueError("'valid_until' must be later than 'valid_from'")

        return self


class AccessGrantsConfig(BaseSettings):
    """Config parameters for checking dataset access."""

    download_access_url: str = Field(
        ...,
        examples=["http://127.0.0.1/download-access"],
        description="URL pointing to the internal download access API.",
    )


class AccessGrantsAdapter(AccessGrantsPort):
    """An adapter for granting access permissions for datasets."""

    def __init__(self, *, config: AccessGrantsConfig, client: httpx.AsyncClient):
        """Configure the access grant adapter."""
        self._url = config.download_access_url
        self._client = client

    @classmethod
    @asynccontextmanager
    async def construct(
        cls, *, config: AccessGrantsConfig
    ) -> AsyncGenerator["AccessGrantsAdapter", None]:
        """Setup AccessGrantsAdapter with the given config."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            yield cls(config=config, client=client)

    async def grant_download_access(  # noqa: PLR0913
        self,
        user_id: str,
        iva_id: str,
        dataset_id: str,
        valid_from: UTCDatetime,
        valid_until: UTCDatetime,
    ) -> None:
        """Grant download access to a given user with an IVA for a given dataset."""
        url = f"{self._url}/users/{user_id}/ivas/{iva_id}/datasets/{dataset_id}"
        try:
            validity = ClaimValidity(valid_from=valid_from, valid_until=valid_until)
        except ValueError as error:
            raise self.AccessGrantsInvalidPeriodError(
                "Invalid validity period"
            ) from error
        try:
            response = await self._client.post(url, content=validity.model_dump_json())
        except httpx.RequestError as error:
            raise self.AccessGrantsError(f"HTTP request error: {error}") from error
        if response.status_code != httpx.codes.NO_CONTENT:
            raise self.AccessGrantsError(
                f"Unexpected HTTP response status code {response.status_code}"
            )
