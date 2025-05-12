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
from datetime import datetime

import httpx
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.opentelemetry import start_span
from pydantic import Field
from pydantic_settings import BaseSettings

from wps.ports.outbound.access import AccessCheckPort

__all__ = ["AccessCheckAdapter", "AccessCheckConfig"]

TIMEOUT = 60


class AccessCheckConfig(BaseSettings):
    """Config parameters for checking dataset access."""

    download_access_url: str = Field(
        ...,
        examples=["http://127.0.0.1/download-access"],
        description="URL pointing to the internal download access API.",
    )


class AccessCheckAdapter(AccessCheckPort):
    """An adapter for checking access permissions for datasets."""

    def __init__(self, *, config: AccessCheckConfig, client: httpx.AsyncClient):
        """Configure the access grant adapter."""
        self._url = config.download_access_url
        self._client = client

    @classmethod
    @asynccontextmanager
    async def construct(
        cls, *, config: AccessCheckConfig
    ) -> AsyncGenerator["AccessCheckAdapter", None]:
        """Setup AccessGrantsAdapter with the given config."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            yield cls(config=config, client=client)

    @start_span()
    async def check_download_access(
        self, user_id: str, dataset_id: str
    ) -> UTCDatetime | None:
        """Check until when the given user has download access for the given dataset."""
        url = f"{self._url}/users/{user_id}/datasets/{dataset_id}"
        response = await self._client.get(url)
        if response.status_code == httpx.codes.OK:
            valid_until = response.json()
            if not valid_until:
                return None
            try:
                return datetime.fromisoformat(valid_until)
            except (ValueError, TypeError) as error:
                raise self.AccessCheckError from error
        if response.status_code == httpx.codes.NOT_FOUND:
            return None
        raise self.AccessCheckError

    @start_span()
    async def get_accessible_datasets_with_expiration(
        self, user_id: str
    ) -> dict[str, UTCDatetime]:
        """Get all datasets that the given user is allowed to download.

        This method returns a mapping from dataset IDs to access expiration dates.
        """
        url = f"{self._url}/users/{user_id}/datasets"
        response = await self._client.get(url)
        if response.status_code == httpx.codes.OK:
            dataset_ids = response.json()
            try:
                return {
                    dataset_id: datetime.fromisoformat(valid_until)
                    for dataset_id, valid_until in dataset_ids.items()
                }
            except (ValueError, TypeError) as error:
                raise self.AccessCheckError from error
        if response.status_code == httpx.codes.NOT_FOUND:
            return {}
        raise self.AccessCheckError
