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


"""Builds a ready-to-use httpx2.AsyncClient from the transports in this package."""

from typing import Any

import httpx2
from httpx2 import Limits

from .config import CompositeConfig
from .factory import (
    BaseTransportFactory,
    CompositeTransportFactory,
    default_base_transport_factory,
)
from .proxy_handling import ratelimiting_retry_proxies
from .ratelimiting import RateBudget


def get_composite_client(
    config: CompositeConfig,
    *,
    limits: Limits | None = None,
    make_base_transport: BaseTransportFactory | None = None,
    trust_env: bool = True,
    **client_kwargs: Any,
) -> httpx2.AsyncClient:
    """Build an AsyncClient that applies retries and rate limiting to every route.

    The client gets one transport for direct requests and one mount per proxy
    environment variable. Each is a base transport wrapped in rate limiting and then
    in retrying. Mounts take precedence for the URLs they match, so a proxied request
    keeps both the proxy and the wrapping.

    All routes share one `RateBudget`, so the configured rate applies to the client as
    a whole rather than to each route on its own.

    Pass `trust_env=False` to not mount any proxies. It does not stop `REQUESTS_CA_BUNDLE`
    and `SSL_CERT_FILE` from determining the CA bundle.

    Extra keyword arguments go to `httpx2.AsyncClient`. The client is always handed a
    transport, so `verify`, `cert`, `http1` and `http2` have no effect. Configure them
    on the transport through `make_base_transport`.

    Raises:
        TypeError: if `proxy` is given. It would replace the whole stack. Set the proxy
            environment variables, or pass `make_base_transport`.
        ValueError: if both `limits` and `make_base_transport` are given. `limits` only
            size the default base transport; pass them to your own factory instead.
    """
    if "proxy" in client_kwargs:
        raise TypeError(
            "get_composite_client() does not accept `proxy`, as it would bypass retries and rate limiting."
            " Set the proxy environment variables or pass a `make_base_transport` instead"
        )
    if limits is not None and make_base_transport is not None:
        raise ValueError(
            "`limits` only apply to the default base transport. Either drop `limits` to use `make_base_transport`"
            " or drop `make_base_transport` to use the default factory with custom `limits`"
        )

    factory = make_base_transport or default_base_transport_factory(limits)
    budget = RateBudget(config)

    return httpx2.AsyncClient(
        transport=CompositeTransportFactory.create_ratelimiting_retry_transport(
            config=config, make_base_transport=factory, proxy=None, budget=budget
        ),
        mounts=ratelimiting_retry_proxies(
            config=config,
            make_base_transport=factory,
            budget=budget,
            trust_env=trust_env,
        ),
        trust_env=trust_env,
        **client_kwargs,
    )
