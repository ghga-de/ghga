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

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

import httpx
from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, Field, HttpUrl
from pydantic_settings import BaseSettings

from wps.constants import TRACER
from wps.ports.outbound.access import AccessCheckPort

__all__ = ["AccessCheckAdapter", "AccessCheckConfig"]

log = logging.getLogger(__name__)

TIMEOUT = 60


class AccessCheckConfig(BaseSettings):
    """Config parameters for checking dataset access."""

    access_url: HttpUrl = Field(
        ...,
        examples=["http://127.0.0.1/"],
        description="Base URL of the internal access API for download and upload",
    )


class AccessCheckAdapter(AccessCheckPort):
    """An adapter for checking access permissions for datasets."""

    def __init__(self, *, config: AccessCheckConfig, client: httpx.AsyncClient):
        """Configure the access grant adapter."""
        base_url = str(config.access_url).rstrip("/")
        self._download_url = f"{base_url}/download-access"
        self._upload_url = f"{base_url}/upload-access"
        self._client = client

    @classmethod
    @asynccontextmanager
    async def construct(
        cls, *, config: AccessCheckConfig
    ) -> AsyncGenerator["AccessCheckAdapter", None]:
        """Setup AccessGrantsAdapter with the given config."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            yield cls(config=config, client=client)

    @TRACER.start_as_current_span("AccessCheckAdapter.check_download_access")
    async def check_download_access(
        self, user_id: UUID, dataset_id: str
    ) -> UTCDatetime | None:
        """Check until when the given user has download access for the given dataset."""
        url = f"{self._download_url}/users/{user_id}/datasets/{dataset_id}"
        response = await self._client.get(url)
        if response.status_code == httpx.codes.OK:
            valid_until = response.json()
            if not valid_until:
                return None
            try:
                return datetime.fromisoformat(valid_until)
            except (ValueError, TypeError) as error:
                log.error(
                    "There was an error extracting the access expiration date from"
                    + " the response from the Access API.",
                    exc_info=True,
                    extra={"user_id": user_id, "dataset_id": dataset_id},
                )
                raise self.AccessCheckError from error
        if response.status_code == httpx.codes.NOT_FOUND:
            return None
        raise self.AccessCheckError

    @TRACER.start_as_current_span(
        "AccessCheckAdapter.get_accessible_datasets_with_expiration"
    )
    async def get_accessible_datasets_with_expiration(
        self, user_id: UUID
    ) -> dict[str, UTCDatetime]:
        """Get all datasets that the given user is allowed to download.

        This method returns a mapping from dataset IDs to access expiration dates.
        """
        url = f"{self._download_url}/users/{user_id}/datasets"
        response = await self._client.get(url)
        if response.status_code == httpx.codes.OK:
            dataset_ids = response.json()
            extra = {"user_id": user_id}
            accessible_datasets: dict[str, UTCDatetime] = {}
            for dataset_id, valid_until in dataset_ids.items():
                try:
                    converted_datetime = datetime.fromisoformat(valid_until)
                    accessible_datasets[dataset_id] = converted_datetime
                except (ValueError, TypeError) as err:
                    log.error(
                        "There was an error converting a datetime (%s) from the access API.",
                        valid_until,
                        extra=extra,
                    )
                    raise self.AccessCheckError from err
            return accessible_datasets
        if response.status_code == httpx.codes.NOT_FOUND:
            return {}
        raise self.AccessCheckError

    @TRACER.start_as_current_span("AccessCheckAdapter.check_upload_access")
    async def check_upload_access(
        self, user_id: UUID, box_id: UUID
    ) -> UTCDatetime | None:
        """Check until when the given user has upload access for the given box."""
        url = f"{self._upload_url}/users/{user_id}/boxes/{box_id}"
        response = await self._client.get(url)
        status_code = response.status_code
        if status_code == httpx.codes.NOT_FOUND:
            return None
        elif status_code != httpx.codes.OK:
            log.error("Call to the access API failed with code %i", status_code)
            raise self.AccessCheckError()
        valid_until = response.json()
        if not valid_until:
            return None
        try:
            return datetime.fromisoformat(valid_until)
        except (ValueError, TypeError) as err:
            log.error(
                "There was an error converting the response (%s) from the access"
                + " API to a datetime.",
                valid_until,
                extra={
                    "valid_until": valid_until,
                    "user_id": user_id,
                    "box_id": box_id,
                },
            )
            raise self.AccessCheckError from err

    @TRACER.start_as_current_span(
        "AccessCheckAdapter.get_accessible_boxes_with_expiration"
    )
    async def get_accessible_boxes_with_expiration(
        self, user_id: UUID
    ) -> dict[UUID4, UTCDatetime]:
        """Get all upload boxes that the given user is allowed to upload to.

        This method returns a mapping from box IDs to access expiration dates.
        """
        url = f"{self._upload_url}/users/{user_id}/boxes"
        response = await self._client.get(url)
        status_code = response.status_code
        if status_code == httpx.codes.NOT_FOUND:
            return {}
        elif status_code != httpx.codes.OK:
            log.error("Call to the access API failed with code %i", status_code)
            raise self.AccessCheckError()
        box_ids = response.json()
        accessible_boxes: dict[UUID4, UTCDatetime] = {}
        for box_id, valid_until in box_ids.items():
            extra = {
                "valid_until": valid_until,
                "user_id": user_id,
                "box_id": box_id,
            }
            try:
                converted_datetime = datetime.fromisoformat(valid_until)
            except (ValueError, TypeError) as err:
                log.error(
                    "There was an error converting a datetime (%s) from the access API.",
                    valid_until,
                    extra=extra,
                )
                raise self.AccessCheckError from err

            try:
                converted_box_id = UUID(box_id)
            except (ValueError, TypeError) as err:
                log.error(
                    "There was an error converting a box ID (%s) to a UUID from the access API.",
                    box_id,
                    extra=extra,
                )
                raise self.AccessCheckError from err

            accessible_boxes[converted_box_id] = converted_datetime
        return accessible_boxes
