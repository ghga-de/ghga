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

"""Mocks of the external HTTP APIs the RS talks to, built on the service commons
`MockRouter`.
"""

__all__ = [
    "AccessApiMock",
    "FileBoxApiMock",
    "ResponseHandler",
    "fail_to_connect",
    "get_mocked_httpx_client",
    "in_sequence",
    "respond",
]

import re
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx2
from ghga_service_commons.api.mock_router import MockRouter

from rs.adapters.outbound.http import (
    AccessApiConfig,
    FileBoxClientConfig,
    get_configured_httpx_client,
)

ResponseHandler = Callable[[httpx2.Request], httpx2.Response]

_PATH_PARAM = re.compile(r"{\w+}")


def _route(path: str) -> str:
    """Turn a FastAPI-style path into a `MockRouter` path pattern.

    Path parameters are matched but not captured - the mock hands the whole request to
    its handlers, which can pick anything they need out of it. The resulting pattern
    also tolerates a query string, which `MockRouter` paths do not do by themselves.
    """
    return _PATH_PARAM.sub(r"(?:[^/?]+)", path) + r"(?:\?.*)?"


def respond(status_code: int, json: Any = None) -> ResponseHandler:
    """Make a handler that always answers with the same status code and JSON body.

    A `json` of `None` means the response carries no body at all.
    """

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status_code=status_code, json=json)

    return handler


def fail_to_connect(reason: str = "All connection attempts failed") -> ResponseHandler:
    """Make a handler that simulates the API being unreachable."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError(reason, request=request)

    return handler


def in_sequence(*handlers: ResponseHandler) -> ResponseHandler:
    """Make a handler that answers consecutive requests with `handlers`, in order.

    Once the handlers are used up, any further request is an error - use this only
    where the exact number of requests is part of what the test asserts.
    """
    remaining = list(handlers)

    def handler(request: httpx2.Request) -> httpx2.Response:
        if not remaining:
            raise AssertionError(f"Unexpected additional request to {request.url}")
        return remaining.pop(0)(request)

    return handler


def _unconfigured(endpoint: str) -> ResponseHandler:
    """Make a handler for an endpoint that the test has not assigned a response to."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise AssertionError(
            f"Unexpected request to {request.url}. Assign a handler to"
            + f" `{endpoint}` if the test is meant to call this endpoint."
        )

    return handler


class _ApiMock:
    """Base class for the mocked APIs, recording every request it answers."""

    def __init__(self, *, url: str) -> None:
        self.base_url = url.rstrip("/")
        self.requests: list[httpx2.Request] = []
        self._router: MockRouter = MockRouter()

    def _path(self, path: str) -> str:
        """Return the routing pattern for `path` relative to this API's base URL."""
        return _route(f"{httpx2.URL(self.base_url).path}{path}")

    def _handle(
        self, request: httpx2.Request, handler: ResponseHandler
    ) -> httpx2.Response:
        """Record the request and let the currently assigned handler answer it."""
        self.requests.append(request)
        return handler(request)

    def as_transport(self) -> httpx2.MockTransport:
        """Return a transport answering this API's requests with this mock."""
        return self._router.as_transport()


class AccessApiMock(_ApiMock):
    """A mock of the access API endpoints that the RS talks to.

    Each endpoint answers with the handler assigned to the corresponding `on_*`
    attribute. Tests can swap those out with `respond(...)`, `in_sequence(...)`,
    `fail_to_connect(...)` or any other callable taking the request. Endpoints without
    an assigned handler raise, so a test never gets a made-up response by accident.
    Every request that reaches the mock is recorded in `requests`.
    """

    def __init__(self, *, config: AccessApiConfig) -> None:
        super().__init__(url=str(config.access_url))

        self.on_grant_upload_access = _unconfigured("on_grant_upload_access")
        self.on_revoke_upload_access = _unconfigured("on_revoke_upload_access")
        self.on_get_upload_access_grants = _unconfigured("on_get_upload_access_grants")
        self.on_get_accessible_upload_boxes = _unconfigured(
            "on_get_accessible_upload_boxes"
        )
        self.on_check_box_access = _unconfigured("on_check_box_access")

        router = self._router

        @router.post(
            self._path("/upload-access/users/{user_id}/ivas/{iva_id}/boxes/{box_id}")
        )
        def grant_upload_access(request: httpx2.Request) -> httpx2.Response:
            return self._handle(request, self.on_grant_upload_access)

        @router.delete(self._path("/upload-access/grants/{grant_id}"))
        def revoke_upload_access(request: httpx2.Request) -> httpx2.Response:
            return self._handle(request, self.on_revoke_upload_access)

        @router.get(self._path("/upload-access/grants"))
        def get_upload_access_grants(request: httpx2.Request) -> httpx2.Response:
            return self._handle(request, self.on_get_upload_access_grants)

        @router.get(self._path("/upload-access/users/{user_id}/boxes"))
        def get_accessible_upload_boxes(request: httpx2.Request) -> httpx2.Response:
            return self._handle(request, self.on_get_accessible_upload_boxes)

        @router.get(self._path("/upload-access/users/{user_id}/boxes/{box_id}"))
        def check_box_access(request: httpx2.Request) -> httpx2.Response:
            return self._handle(request, self.on_check_box_access)


class FileBoxApiMock(_ApiMock):
    """A mock of the FileUploadBox endpoints of the owning service (the UCS).

    Handlers are assigned and requests are recorded just like in `AccessApiMock`. Note
    that locking, unlocking, archiving and resizing a box all go through the same
    `PATCH` endpoint and hence share `on_update_file_upload_box`.
    """

    def __init__(self, *, config: FileBoxClientConfig) -> None:
        super().__init__(url=str(config.ucs_url))

        self.on_create_file_upload_box = _unconfigured("on_create_file_upload_box")
        self.on_update_file_upload_box = _unconfigured("on_update_file_upload_box")
        self.on_get_file_upload_list = _unconfigured("on_get_file_upload_list")
        self.on_delete_file_upload = _unconfigured("on_delete_file_upload")
        self.on_delete_file_upload_box = _unconfigured("on_delete_file_upload_box")

        router = self._router

        @router.post(self._path("/boxes"))
        def create_file_upload_box(request: httpx2.Request) -> httpx2.Response:
            return self._handle(request, self.on_create_file_upload_box)

        @router.patch(self._path("/boxes/{box_id}"))
        def update_file_upload_box(request: httpx2.Request) -> httpx2.Response:
            return self._handle(request, self.on_update_file_upload_box)

        @router.get(self._path("/boxes/{box_id}/uploads"))
        def get_file_upload_list(request: httpx2.Request) -> httpx2.Response:
            return self._handle(request, self.on_get_file_upload_list)

        @router.delete(self._path("/boxes/{box_id}/uploads/{file_id}"))
        def delete_file_upload(request: httpx2.Request) -> httpx2.Response:
            return self._handle(request, self.on_delete_file_upload)

        @router.delete(self._path("/boxes/{box_id}"))
        def delete_file_upload_box(request: httpx2.Request) -> httpx2.Response:
            return self._handle(request, self.on_delete_file_upload_box)


class _RoutingTransport(httpx2.AsyncBaseTransport):
    """Dispatches requests to the mock of the API they are addressed to."""

    def __init__(self, mocks: list[_ApiMock]) -> None:
        self._routes = [(mock.base_url, mock.as_transport()) for mock in mocks]

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Hand the request to the mock whose base URL it starts with."""
        url = str(request.url)
        for base_url, transport in self._routes:
            if url.startswith(base_url):
                return await transport.handle_async_request(request)
        raise AssertionError(f"Request to unmocked URL {url}")


@asynccontextmanager
async def get_mocked_httpx_client(
    *, access_api: AccessApiMock, file_box_api: FileBoxApiMock
) -> AsyncGenerator[httpx2.AsyncClient]:
    """Drop-in for `get_configured_httpx_client` that answers all outbound calls with
    the given mocks instead of sending them over the network.
    """
    async with get_configured_httpx_client(
        base_transport=_RoutingTransport([access_api, file_box_api])
    ) as client:
        yield client
