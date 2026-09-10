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
"""What the mocked GHGA APIs share: response shapes and the health check stand-in."""

import json
from typing import Any

import httpx2

from ghga_service_commons.api.mock_api import (
    MockedApi,
    MockedApis,
    any_network,
    endpoint,
    respond,
)
from tests.fixtures.config import get_test_config

__all__ = [
    "DOWNLOAD_API_URL",
    "HEALTH_CHECKED_URLS",
    "MOCK_API_HOST",
    "STORAGE_URL",
    "UPLOAD_API_URL",
    "WORK_PACKAGE_API_URL",
    "httpyexpect_error",
    "mock_health_checks",
]

# The host the mocked GHGA APIs are served from. The other spellings of the loopback
# interface reach them too - `MockedApis` folds those onto one spelling itself.
MOCK_API_HOST = "127.0.0.1"

# Where the mocked APIs live. `set_runtime_test_config` points the connector's own
# config at these same URLs, and the WKVS mock announces them, so a unit test and an
# integration test reach the same mocks by the same addresses.
UPLOAD_API_URL = f"http://{MOCK_API_HOST}/upload"
DOWNLOAD_API_URL = f"http://{MOCK_API_HOST}/download"
WORK_PACKAGE_API_URL = f"http://{MOCK_API_HOST}/work"
# Stands in for object storage, which in integration tests is the S3 testcontainer at a
# real address. Presigned URLs the mocks hand out live under here.
STORAGE_URL = f"http://{MOCK_API_HOST}/storage"

# The APIs the connector health checks before it talks to them.
HEALTH_CHECKED_URLS = (
    get_test_config().wkvs_api_url,
    UPLOAD_API_URL,
    DOWNLOAD_API_URL,
    WORK_PACKAGE_API_URL,
)


def httpyexpect_error(
    status_code: int, exception_id: str, description: str, data: dict[str, Any]
) -> httpx2.Response:
    """The response a GHGA service sends for an error, in the httpyexpect schema.

    `data` is serialized leniently, because it does not always hold plain JSON.
    """
    body = {"exception_id": exception_id, "description": description, "data": data}
    return httpx2.Response(
        status_code,
        content=json.dumps(body, default=str),
        headers={"content-type": "application/json"},
    )


class MockedHealthApi(MockedApi):
    """Answers the health endpoint of one API, reporting it as reachable."""

    on_health = endpoint("GET", "/health", respond(200, json={"status": "OK"}))


class _UnreachableTransport(httpx2.BaseTransport, httpx2.AsyncBaseTransport):
    """Refuses to connect, the way a service that is down would."""

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        """Refuse the connection."""
        raise httpx2.ConnectError("mocked connection failure", request=request)

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Refuse the connection."""
        raise httpx2.ConnectError("mocked connection failure", request=request)


def mock_health_checks(
    monkeypatch, *, reachable: bool = True, healthy_url: str | None = None
) -> None:
    """Report the services the connector health checks as reachable or unreachable.

    `healthy_url` names the one API URL to report as healthy, which also pins down which
    URL `is_service_healthy` derives its health endpoint from; without it every mocked
    API is healthy. Anything not reported as healthy refuses the connection.

    `is_service_healthy` checks health endpoints with a module level `httpx2.get` rather
    than the client built by `async_client`, so those calls cannot be routed through the
    client's transport and `httpx2.get` itself has to be replaced.
    """
    urls = [healthy_url] if healthy_url else list(HEALTH_CHECKED_URLS)
    healthy = [MockedHealthApi(url) for url in urls] if reachable else []
    # everything is let out, so that whatever no mock answers hits the refusing
    # transport underneath and looks like a service that is down
    transport = MockedApis(*healthy, allow_network=any_network).as_transport(
        _UnreachableTransport()
    )

    def mock_get(*args: Any, **kwargs: Any) -> httpx2.Response:
        """Stand in for `httpx2.get`, answering from the health mocks.

        The signature mirrors `httpx2.get` rather than the call `check_url` happens to
        make, so rewriting that call site doesn't break the stand-in.
        """
        with httpx2.Client(transport=transport) as client:
            return client.get(*args, **kwargs)

    monkeypatch.setattr(httpx2, "get", mock_get)
