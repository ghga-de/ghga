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

"""Mocks of the external APIs the RS calls, built on the service commons `ApiMock`."""

__all__ = [
    "AccessApiMock",
    "FileBoxApiMock",
    "get_mocked_httpx_client",
]

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx2

from ghga_service_commons.api.mock_api import ApiMock, RoutingTransport, endpoint
from rs.adapters.outbound.http import (
    AccessApiConfig,
    FileBoxClientConfig,
    get_configured_httpx_client,
)

UPLOAD_ACCESS_PATH = "/upload-access"
USER_PATH = f"{UPLOAD_ACCESS_PATH}/users/{{user_id}}"


class AccessApiMock(ApiMock):
    """A mock of the access API endpoints that the RS talks to.

    Each endpoint answers with the handler assigned to the corresponding `on_*`
    attribute. Tests can swap those out with `respond(...)`, `in_sequence(...)`,
    `fail_to_connect(...)` or any other callable taking the request. Endpoints without
    an assigned handler raise, so a test never gets a made-up response by accident.
    Every request that reaches the mock is recorded in `requests`.
    """

    on_grant_upload_access = endpoint(
        "POST", f"{USER_PATH}/ivas/{{iva_id}}/boxes/{{box_id}}"
    )
    on_revoke_upload_access = endpoint(
        "DELETE", f"{UPLOAD_ACCESS_PATH}/grants/{{grant_id}}"
    )
    on_get_upload_access_grants = endpoint("GET", f"{UPLOAD_ACCESS_PATH}/grants")
    on_get_accessible_upload_boxes = endpoint("GET", f"{USER_PATH}/boxes")
    on_check_box_access = endpoint("GET", f"{USER_PATH}/boxes/{{box_id}}")

    def __init__(self, *, config: AccessApiConfig) -> None:
        """Serve the access API where the given config expects it."""
        super().__init__(base_url=str(config.access_url))


class FileBoxApiMock(ApiMock):
    """A mock of the FileUploadBox endpoints of the owning service (the UCS).

    Handlers are assigned and requests are recorded just like in `AccessApiMock`. Note
    that locking, unlocking, archiving and resizing a box all go through the same
    `PATCH` endpoint and hence share `on_update_file_upload_box`.
    """

    on_create_file_upload_box = endpoint("POST", "/boxes")
    on_update_file_upload_box = endpoint("PATCH", "/boxes/{box_id}")
    on_get_file_upload_list = endpoint("GET", "/boxes/{box_id}/uploads")
    on_delete_file_upload = endpoint("DELETE", "/boxes/{box_id}/uploads/{file_id}")
    on_delete_file_upload_box = endpoint("DELETE", "/boxes/{box_id}")

    def __init__(self, *, config: FileBoxClientConfig) -> None:
        """Serve the UCS API where the given config expects it."""
        super().__init__(base_url=str(config.ucs_url))


@asynccontextmanager
async def get_mocked_httpx_client(
    *, access_api: AccessApiMock, file_box_api: FileBoxApiMock
) -> AsyncGenerator[httpx2.AsyncClient]:
    """Answer every outbound call with the given mocks instead of the network.

    A drop-in for `get_configured_httpx_client`, keeping the retry and rate limiting
    layers the service configures in place below the client.
    """
    async with get_configured_httpx_client(
        base_transport=RoutingTransport(access_api, file_box_api)
    ) as client:
        yield client
