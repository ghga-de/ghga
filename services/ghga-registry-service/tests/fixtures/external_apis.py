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
"""Mocks of the external HTTP APIs the RS talks to, built on `MockedApi`."""

__all__ = [
    "AccessApiMock",
    "FileBoxApiMock",
    "get_mocked_httpx_client",
]

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx2

from ghga_service_commons.api.mock_api import (
    MockedApi,
    MockedApis,
    endpoint,
    no_network,
)
from rs.adapters.outbound.http import (
    AccessApiConfig,
    FileBoxClientConfig,
    get_configured_httpx_client,
)


class AccessApiMock(MockedApi):
    """A mock of the access API endpoints that the RS talks to.

    Each endpoint answers with the handler assigned to the corresponding `on_*`
    attribute. Tests can swap those out with `respond(...)`, `in_sequence(...)`,
    `fail_to_connect(...)` or any other callable taking the request. Endpoints without
    an assigned handler raise, so a test never gets a made-up response by accident.
    Every request that reaches the mock is recorded in `requests`.
    """

    on_grant_upload_access = endpoint(
        "POST", "/upload-access/users/{user_id}/ivas/{iva_id}/boxes/{box_id}"
    )
    on_revoke_upload_access = endpoint("DELETE", "/upload-access/grants/{grant_id}")
    on_get_upload_access_grants = endpoint("GET", "/upload-access/grants")
    on_get_accessible_upload_boxes = endpoint(
        "GET", "/upload-access/users/{user_id}/boxes"
    )
    on_check_box_access = endpoint(
        "GET", "/upload-access/users/{user_id}/boxes/{box_id}"
    )

    def __init__(self, *, config: AccessApiConfig) -> None:
        """Serve the access API where the config says it is."""
        super().__init__(str(config.access_url))


class FileBoxApiMock(MockedApi):
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
        """Serve the file box API where the config says it is."""
        super().__init__(str(config.ucs_url))


@asynccontextmanager
async def get_mocked_httpx_client(
    *, access_api: AccessApiMock, file_box_api: FileBoxApiMock
) -> AsyncGenerator[httpx2.AsyncClient]:
    """Answer every outbound call with the given mocks instead of the network."""
    # nothing may go out: a URL neither mock serves is a test reaching somewhere it
    # did not mean to, not something to send on
    served = MockedApis(access_api, file_box_api, allow_network=no_network)
    async with get_configured_httpx_client(
        base_transport=served.as_transport()
    ) as client:
        yield client
