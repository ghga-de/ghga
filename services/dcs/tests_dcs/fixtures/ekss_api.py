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
    "ENVELOPE",
    "SECRET_ID",
    "EkssApiMock",
    "ResponseHandler",
    "fail_to_connect",
    "respond",
    "secret_not_found",
]

from collections.abc import Callable
from typing import Any

import httpx2
from fastapi import status

from dcs.adapters.outbound.http.secrets import (
    DELETION_PATH,
    ENVELOPE_PATH,
    SecretsClientConfig,
)
from ghga_service_commons.api.mock_router import MockRouter

ResponseHandler = Callable[[httpx2.Request], httpx2.Response]

SECRET_ID = "some-secret"

ENVELOPE = (
    "pfAcB7o2lz0075VTpb6b5PCdfWnPofyZ62RYxQ6gZflUoCuwSt//R2N6QCWTnn7wV/oU8syQBCgB/1KTqz77v"
    + "8jBF73IyszJzVezDokPe8AJIEFG18luo/ZRI9mDSEI/GFy2EtNdflqW+CBSgUEWiQjkRAwS3V+dVeFsVQ=="
)


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


def secret_not_found() -> ResponseHandler:
    """Make a handler answering with the httpyexpect body for an unknown secret."""
    return respond(
        status.HTTP_404_NOT_FOUND,
        json={
            "exception_id": "secretNotFoundError",
            "description": "The secret for the given id was not found.",
            "data": {},
        },
    )


class EkssApiMock:
    """A mock of the EKSS API endpoints that the DCS talks to.

    Each endpoint answers with the handler assigned to `on_get_envelope` or
    `on_delete_secret`. Tests can swap those out with `respond(...)`,
    `fail_to_connect(...)`, `secret_not_found()` or any other callable taking the
    request. Every request that reaches the mock is recorded in `requests`.

    The transport returned by `as_transport()` answers *every* request, so a test
    using it cannot accidentally reach the network - a URL that matches no registered
    endpoint gets a 404 from the router rather than being sent out.
    """

    def __init__(self, *, config: SecretsClientConfig) -> None:
        base_path = httpx2.URL(config.ekss_base_url).path.rstrip("/")

        self.requests: list[httpx2.Request] = []
        self.on_get_envelope: ResponseHandler = respond(
            status.HTTP_200_OK, json={"content": ENVELOPE}
        )
        self.on_delete_secret: ResponseHandler = respond(status.HTTP_204_NO_CONTENT)

        router: MockRouter = MockRouter()

        @router.get(f"{base_path}{ENVELOPE_PATH}")
        def get_envelope(
            secret_id: str, receiver_public_key: str, request: httpx2.Request
        ) -> httpx2.Response:
            return self._handle(request, self.on_get_envelope)

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
