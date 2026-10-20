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

"""Mocks of the APIs the datasteward kit calls, built on the service commons `MockApi`.

The kit's synchronous calls build their own `httpx2` client or call `httpx2.get`, so
`serve_httpx2_from` redirects what `httpx2` hands out.
"""

__all__ = ["WkvsMock", "serve_httpx2_from"]

from typing import Any

import httpx2
import pytest

from ghga_service_commons.http.mock_api import MockApi, ResponseHandler, respond


class WkvsMock(MockApi):
    """A mock of the well-known value service, serving the storage aliases."""

    def __init__(self, base_url: str, storage_aliases: dict[str, str]) -> None:
        super().__init__(base_url)
        self.on_get_storage_aliases: ResponseHandler = respond(
            200, json={"storage_aliases": storage_aliases}
        )
        self.route("GET", "/values/storage_aliases", "on_get_storage_aliases")


def serve_httpx2_from(
    monkeypatch: pytest.MonkeyPatch, transport: httpx2.BaseTransport
) -> None:
    """Answer the requests of the clients `httpx2` hands out from `transport`."""
    # bound before patching, so the replacements below don't call themselves
    real_client = httpx2.Client

    def mocked_client(**kwargs: Any) -> httpx2.Client:
        return real_client(transport=transport, **kwargs)

    def mocked_get(url: Any, **kwargs: Any) -> httpx2.Response:
        with mocked_client() as client:
            return client.get(url, **kwargs)

    monkeypatch.setattr(httpx2, "Client", mocked_client)
    monkeypatch.setattr(httpx2, "get", mocked_get)
