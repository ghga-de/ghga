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

"""Builds the transport and proxy mounts that give an httpx2.AsyncClient this stack."""

from typing import TypedDict

from httpx2 import AsyncBaseTransport

from .config import TransportConfig
from .factory import (
    BaseTransportFactory,
    CompositeTransportFactory,
    default_base_transport_factory,
)
from .proxy_handling import ratelimiting_retry_proxies


class ClientRoutes(TypedDict):
    """The `transport` and `mounts` keyword arguments of an `httpx2.AsyncClient`."""

    transport: AsyncBaseTransport
    mounts: dict[str, AsyncBaseTransport | None]


def client_routes(
    config: TransportConfig,
    *,
    make_base_transport: BaseTransportFactory | None = None,
) -> ClientRoutes:
    """Build a client's transport and proxy mounts with retries and rate limiting.

    httpx2 ignores the proxy environment variables once it is handed a transport, so
    this builds one mount per proxy variable next to the direct transport. All of them
    come from the same base transport factory and get the same wrapping.

    The client ignores `verify`, `cert`, `http1`, `http2` and `limits`, as it is always
    handed a transport. Set them in `make_base_transport` instead, for example
    `default_base_transport_factory(limits=limits)`. Set the proxy environment
    variables instead of passing `proxy` to the client: httpx2 would send every URL
    that no mount claims through that proxy, without retries or rate limiting.

    Example:
        ```
        async with httpx2.AsyncClient(
            timeout=30.0, **client_routes(config)
        ) as client:
            response = await client.get(url)
        ```
    """
    factory = make_base_transport or default_base_transport_factory()
    return {
        "transport": CompositeTransportFactory.create_ratelimiting_retry_transport(
            config, make_base_transport=factory
        ),
        "mounts": ratelimiting_retry_proxies(config, make_base_transport=factory),
    }
