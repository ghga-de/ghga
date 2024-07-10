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
from pydantic import Field
from pydantic_settings import BaseSettings

from wps.ports.outbound.access import AccessCheckPort

__all__ = ["AccessCheckConfig", "AccessCheckAdapter"]

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

    async def check_download_access(self, user_id: str, dataset_id: str) -> bool:
        """Check whether the given user has download access for the given dataset."""
        url = f"{self._url}/users/{user_id}/datasets/{dataset_id}"
        response = await self._client.get(url)
        if response.status_code == httpx.codes.OK:
            return response.json() is True
        if response.status_code == httpx.codes.NOT_FOUND:
            return False
        raise self.AccessCheckError

    async def get_datasets_with_download_access(self, user_id: str) -> list[str]:
        """Get all datasets that the given user is allowed to download."""
        url = f"{self._url}/users/{user_id}/datasets"
        response = await self._client.get(url)
        if response.status_code == httpx.codes.OK:
            return response.json()
        if response.status_code == httpx.codes.NOT_FOUND:
            return []
        raise self.AccessCheckError
