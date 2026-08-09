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

"""A mock of the EKSS API, built on the service commons `MockRouter`."""

__all__ = [
    "DEPOSITED_SECRET_ID",
    "EkssApiMock",
    "ResponseHandler",
    "fail_to_connect",
    "respond",
]

from collections.abc import Callable
from typing import Any

import httpx2
from fastapi import status

from fis.adapters.outbound.secrets import (
    DELETION_PATH,
    DEPOSIT_PATH,
    SecretsClientConfig,
)
from ghga_service_commons.api.mock_router import MockRouter

ResponseHandler = Callable[[httpx2.Request], httpx2.Response]

DEPOSITED_SECRET_ID = "some-secret-id"


def respond(status_code: int, json: Any = None) -> ResponseHandler:
    """Make a handler that always answers with the same status code and JSON body.

    A `json` of `None` means the response carries no body at all.
    """

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status_code=status_code, json=json)

    return handler


def fail_to_connect(reason: str = "All connection attempts failed") -> ResponseHandler:
    """Make a handler that simulates the EKSS API being unreachable."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError(reason, request=request)

    return handler


class EkssApiMock:
    """A mock of the EKSS API endpoints that the FIS talks to.

    Each endpoint answers with the handler assigned to `on_deposit_secret` or
    `on_delete_secret`. Tests can swap those out with `respond(...)`,
    `fail_to_connect(...)` or any other callable taking the request. Every request
    that reaches the mock is recorded in `requests`.

    The transport returned by `as_transport()` answers *every* request, so a test
    using it cannot accidentally reach the network - a URL that matches no registered
    endpoint gets a 404 from the router rather than being sent out.
    """

    def __init__(self, *, config: SecretsClientConfig) -> None:
        base_path = httpx2.URL(str(config.ekss_api_url)).path.rstrip("/")

        self.requests: list[httpx2.Request] = []
        self.on_deposit_secret: ResponseHandler = respond(
            status.HTTP_201_CREATED, json={"secret_id": DEPOSITED_SECRET_ID}
        )
        self.on_delete_secret: ResponseHandler = respond(status.HTTP_204_NO_CONTENT)

        router: MockRouter = MockRouter()

        @router.post(f"{base_path}{DEPOSIT_PATH}")
        def deposit_secret(request: httpx2.Request) -> httpx2.Response:
            return self._handle(request, self.on_deposit_secret)

        @router.delete(f"{base_path}{DELETION_PATH}")
        def delete_secret(secret_id: str, request: httpx2.Request) -> httpx2.Response:
            return self._handle(request, self.on_delete_secret)

        self._router = router

    def _handle(
        self, request: httpx2.Request, handler: ResponseHandler
    ) -> httpx2.Response:
        """Record the request and let the currently assigned handler answer it."""
        self.requests.append(request)
        return handler(request)

    def as_transport(self) -> httpx2.MockTransport:
        """Return a transport answering EKSS API requests with this mock."""
        return self._router.as_transport()
