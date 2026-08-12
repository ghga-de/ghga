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

"""A mock of the access API, built on the service commons `MockRouter`."""

from collections.abc import Callable
from json import dumps as json_dumps
from typing import Any

import httpx2

from ghga_service_commons.api.mock_router import MockRouter
from wps.adapters.outbound.http import AccessCheckConfig

__all__ = ["AccessApiMock", "ResponseHandler", "respond"]

ResponseHandler = Callable[[httpx2.Request], httpx2.Response]

_NO_BODY = object()  # marker distinguishing "no body" from a JSON body of `null`


def respond(status_code: int = 200, *, json: Any = _NO_BODY) -> ResponseHandler:
    """Make a handler that always answers with the same status code and JSON body.

    When `json` is not passed at all, the response carries no body.
    """

    def handler(request: httpx2.Request) -> httpx2.Response:
        if json is _NO_BODY:
            return httpx2.Response(status_code)
        return httpx2.Response(
            status_code,
            content=json_dumps(json),
            headers={"Content-Type": "application/json"},
        )

    return handler


class AccessApiMock:
    """A mock of the access API endpoints that the work package service talks to.

    Each endpoint answers with the handler currently assigned to
    `on_check_download_access`, `on_get_accessible_datasets`, `on_check_upload_access`
    or `on_get_accessible_boxes`. Tests can swap those out with `respond(...)` or any
    other callable taking the request. Every request that reaches the mock is recorded
    in `requests`, so tests can assert which URL was actually requested.

    The transport returned by `as_transport()` answers *every* request, meaning a
    request to an unregistered path raises instead of reaching the network.
    """

    def __init__(self, *, config: AccessCheckConfig) -> None:
        base_path = httpx2.URL(str(config.access_url)).path.rstrip("/")
        download_path = f"{base_path}/download-access/users/{{user_id}}"
        upload_path = f"{base_path}/upload-access/users/{{user_id}}"

        self.requests: list[httpx2.Request] = []
        self.on_check_download_access: ResponseHandler = respond(json=None)
        self.on_get_accessible_datasets: ResponseHandler = respond(json={})
        self.on_check_upload_access: ResponseHandler = respond(json=None)
        self.on_get_accessible_boxes: ResponseHandler = respond(json={})

        router: MockRouter = MockRouter()

        @router.get(f"{download_path}/datasets/{{dataset_id}}")
        def check_download_access(
            user_id: str, dataset_id: str, request: httpx2.Request
        ) -> httpx2.Response:
            return self._handle(request, self.on_check_download_access)

        @router.get(f"{download_path}/datasets")
        def get_accessible_datasets(
            user_id: str, request: httpx2.Request
        ) -> httpx2.Response:
            return self._handle(request, self.on_get_accessible_datasets)

        @router.get(f"{upload_path}/boxes/{{box_id}}")
        def check_upload_access(
            user_id: str, box_id: str, request: httpx2.Request
        ) -> httpx2.Response:
            return self._handle(request, self.on_check_upload_access)

        @router.get(f"{upload_path}/boxes")
        def get_accessible_boxes(
            user_id: str, request: httpx2.Request
        ) -> httpx2.Response:
            return self._handle(request, self.on_get_accessible_boxes)

        self._router = router

    def _handle(
        self, request: httpx2.Request, handler: ResponseHandler
    ) -> httpx2.Response:
        """Record the request and let the currently assigned handler answer it."""
        self.requests.append(request)
        return handler(request)

    @property
    def last_url(self) -> str:
        """The URL of the most recent request that reached the mock."""
        return str(self.requests[-1].url)

    def as_transport(self) -> httpx2.AsyncBaseTransport:
        """Return a transport answering access API requests with this mock."""
        return self._router.as_transport()
