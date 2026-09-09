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
"""Mocks of the HTTP APIs the data steward kit calls.

Each API is modeled by a `MockedApi` declaring the endpoints it serves, and a test says
how the ones it cares about answer by assigning to their `on_*` attributes. Anything no
mock serves raises instead of reaching the network.
"""

__all__ = [
    "WKVS_API_URL",
    "MockedIngestApi",
    "MockedRetryApi",
    "MockedWkvsApi",
    "serve_httpx",
]

from typing import Any

import httpx2
import pytest

from ghga_service_commons.api.mock_api import (
    MockedApi,
    MockedApis,
    endpoint,
    no_network,
)

# where the WKVS lives unless a test's config says otherwise
WKVS_API_URL = "https://data.ghga.de/.well-known"


class MockedWkvsApi(MockedApi):
    """The well-known-value-service the kit looks its configured values up in."""

    on_get_value = endpoint("GET", "/values/{value_name}")


class MockedIngestApi(MockedApi):
    """The file ingest service the kit submits file metadata to.

    Which path it is served under is configuration, so a test subclasses this and
    redeclares `on_ingest` with the endpoint its run is configured for.
    """

    on_ingest = endpoint("POST", "/ingest")


class MockedRetryApi(MockedApi):
    """The one endpoint the retry and rate limiting layers are exercised against."""

    base_url = "http://not-a-real-url"

    on_get = endpoint("GET", "/test")


def serve_httpx(monkeypatch: pytest.MonkeyPatch, *apis: MockedApi) -> None:
    """Route the clients that `httpx2` hands out through `apis`.

    The synchronous ingest and deletion paths instantiate their own client and take no
    transport, so there is no way to inject one from the outside.
    """
    transport = MockedApis(*apis, allow_network=no_network).as_transport()
    # bound before patching, so the replacements below don't call themselves
    real_client = httpx2.Client

    def mocked_client(**kwargs: Any) -> httpx2.Client:
        """Hand out a client that answers from the mocks."""
        return real_client(transport=transport, **kwargs)

    def mocked_get(url: Any, **kwargs: Any) -> httpx2.Response:
        """Stand in for `httpx2.get`, answering from the mocks."""
        with mocked_client() as client:
            return client.get(url, **kwargs)

    monkeypatch.setattr(httpx2, "Client", mocked_client)
    monkeypatch.setattr(httpx2, "get", mocked_get)
