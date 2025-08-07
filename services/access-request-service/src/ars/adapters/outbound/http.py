# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from typing import Any

import httpx
from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, Field, ValidationError
from pydantic_settings import BaseSettings

from ars.core.models import BaseAccessGrant, GrantValidity
from ars.ports.outbound.access_grants import AccessGrantsPort

__all__ = ["AccessGrantsAdapter", "AccessGrantsConfig"]

TIMEOUT = 60


class AccessGrantsConfig(BaseSettings):
    """Config parameters for checking dataset access."""

    download_access_url: str = Field(
        ...,
        examples=["http://127.0.0.1/download-access"],
        description="URL pointing to the internal download access API.",
    )


class AccessGrantsAdapter(AccessGrantsPort):
    """An adapter for checking and granting access permissions for datasets.

    This adapter proxies requests to the claims repository service
    which can be accessed only internally for security reasons.
    """

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

    async def grant_download_access(
        self,
        user_id: UUID4,
        iva_id: UUID4,
        dataset_id: str,
        valid_from: UTCDatetime,
        valid_until: UTCDatetime,
    ) -> None:
        """Grant download access to a given user with an IVA for a given dataset.

        May raise an `AccessGrantsInvalidPeriodError` or a general `AccessGrantsError`.
        """
        url = f"{self._url}/users/{user_id}/ivas/{iva_id}/datasets/{dataset_id}"
        try:
            validity = GrantValidity(valid_from=valid_from, valid_until=valid_until)
        except ValidationError as error:
            raise self.AccessGrantsInvalidPeriodError(
                "Invalid validity period"
            ) from error
        try:
            response = await self._client.post(url, content=validity.model_dump_json())
        except httpx.RequestError as error:
            raise self.AccessGrantsError(f"HTTP request error: {error}") from error
        if response.status_code != httpx.codes.NO_CONTENT:
            raise self.AccessGrantsError(
                f"Unexpected response status code {response.status_code}"
            )

    async def get_download_access_grants(
        self,
        user_id: UUID4 | None = None,
        iva_id: UUID4 | None = None,
        dataset_id: str | None = None,
        valid: bool | None = None,
    ) -> list[BaseAccessGrant]:
        """Get download access grants.

        You can filter the grants by user ID, IVA ID, dataset ID and whether the grant
        is currently valid or not.

        May raise an `AccessGrantsError`.
        """
        url = f"{self._url}/grants"
        params: dict[str, Any] = {}
        if user_id is not None:
            params["user_id"] = user_id
        if iva_id is not None:
            params["iva_id"] = iva_id
        if dataset_id is not None:
            params["dataset_id"] = dataset_id
        if valid is not None:
            params["valid"] = str(valid).lower()
        try:
            response = await self._client.get(url, params=params)
        except httpx.RequestError as error:
            raise self.AccessGrantsError(f"HTTP request error: {error}") from error
        if response.status_code != httpx.codes.OK:
            raise self.AccessGrantsError(
                f"Unexpected response status code {response.status_code}"
            )
        response_data = response.json()
        if not isinstance(response_data, list):
            raise self.AccessGrantsError(
                "Unexpected response data format: expected an array"
            )
        try:
            return [BaseAccessGrant(**grant_data) for grant_data in response_data]
        except ValidationError as error:
            raise self.AccessGrantsError(
                f"Invalid data in response: {error}"
            ) from error

    async def revoke_download_access_grant(self, grant_id: UUID4) -> None:
        """Revoke a download access grant.

        May raise an `AccessGrantNotFoundError` or a general `AccessGrantsError`.
        """
        ...
        url = f"{self._url}/grants/{grant_id}"
        try:
            response = await self._client.delete(url)
        except httpx.RequestError as error:
            raise self.AccessGrantsError(f"HTTP request error: {error}") from error
        if response.status_code == httpx.codes.NOT_FOUND:
            raise self.AccessGrantNotFoundError(f"Grant with ID {grant_id} not found")
        if response.status_code != httpx.codes.NO_CONTENT:
            raise self.AccessGrantsError(
                f"Unexpected response status code {response.status_code}"
            )
