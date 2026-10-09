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

"""Mocks of the external HTTP APIs the RS talks to, built on `MockApi`."""

__all__ = ["AccessApiMock", "FileBoxApiMock", "get_mocked_httpx_client"]

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx2

from ghga_service_commons.http.mock_api import (
    MockApi,
    NotMockedError,
    ResponseHandler,
    serve,
)
from rs.adapters.outbound.http import (
    AccessApiConfig,
    FileBoxClientConfig,
    get_configured_httpx_client,
)


def _unconfigured(request: httpx2.Request) -> httpx2.Response:
    """Refuse a request to an endpoint the test has not assigned a handler to."""
    raise NotMockedError(f"Assign an `on_*` handler for {request.method} {request.url}")


class AccessApiMock(MockApi):
    """A mock of the access API endpoints the RS calls, each failing until assigned."""

    def __init__(self, *, config: AccessApiConfig) -> None:
        super().__init__(str(config.access_url))
        self.on_grant_upload_access: ResponseHandler = _unconfigured
        self.on_get_upload_access_grants: ResponseHandler = _unconfigured
        self.on_get_accessible_upload_boxes: ResponseHandler = _unconfigured
        self.on_check_box_access: ResponseHandler = _unconfigured
        self.route(
            "POST",
            "/upload-access/users/{user_id}/ivas/{iva_id}/boxes/{box_id}",
            "on_grant_upload_access",
        )
        self.route("GET", "/upload-access/grants", "on_get_upload_access_grants")
        self.route(
            "GET",
            "/upload-access/users/{user_id}/boxes",
            "on_get_accessible_upload_boxes",
        )
        self.route(
            "GET",
            "/upload-access/users/{user_id}/boxes/{box_id}",
            "on_check_box_access",
        )


class FileBoxApiMock(MockApi):
    """A mock of the UCS's FileUploadBox endpoints, each failing until assigned.

    Locking, unlocking, archiving and resizing a box share `on_update_file_upload_box`.
    """

    def __init__(self, *, config: FileBoxClientConfig) -> None:
        super().__init__(str(config.ucs_url))
        self.on_create_file_upload_box: ResponseHandler = _unconfigured
        self.on_update_file_upload_box: ResponseHandler = _unconfigured
        self.on_get_file_upload_list: ResponseHandler = _unconfigured
        self.on_delete_file_upload: ResponseHandler = _unconfigured
        self.on_delete_file_upload_box: ResponseHandler = _unconfigured
        self.on_requeue_single_file_upload: ResponseHandler = _unconfigured
        self.on_requeue_all_box_uploads: ResponseHandler = _unconfigured
        self.route("POST", "/boxes", "on_create_file_upload_box")
        self.route("PATCH", "/boxes/{box_id}", "on_update_file_upload_box")
        self.route("GET", "/boxes/{box_id}/uploads", "on_get_file_upload_list")
        self.route(
            "DELETE", "/boxes/{box_id}/uploads/{file_id}", "on_delete_file_upload"
        )
        self.route("DELETE", "/boxes/{box_id}", "on_delete_file_upload_box")
        self.route(
            "POST",
            "/rpc/boxes/{box_id}/uploads/{file_id}/requeue",
            "on_requeue_single_file_upload",
        )
        self.route("POST", "/rpc/boxes/{box_id}/requeue", "on_requeue_all_box_uploads")


@asynccontextmanager
async def get_mocked_httpx_client(
    *, access_api: AccessApiMock, file_box_api: FileBoxApiMock
) -> AsyncGenerator[httpx2.AsyncClient]:
    """Like `get_configured_httpx_client`, answering outbound calls from the mocks."""
    async with get_configured_httpx_client(
        base_transport=serve(access_api, file_box_api)
    ) as client:
        yield client
