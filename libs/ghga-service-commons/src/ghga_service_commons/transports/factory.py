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

"""Provides factories for different flavors of httpx2.AsyncHTTPTransport."""

import os
import ssl
import warnings
from collections.abc import Callable
from typing import Any

from httpx2 import AsyncBaseTransport, AsyncHTTPTransport, Limits

from .config import CompositeConfig
from .ratelimiting import AsyncRateLimitingTransport, RateBudget
from .retry import AsyncRetryTransport

BaseTransportFactory = Callable[[str | None], AsyncBaseTransport]


def get_ssl_verify() -> ssl.SSLContext | bool:
    """SSL verification setting for outgoing transports.

    Honors ``REQUESTS_CA_BUNDLE`` and ``SSL_CERT_FILE`` (the variables ``requests``,
    ``urllib3`` and boto3 use), so deployments behind SSL-inspecting proxies or with a
    custom CA verify correctly. ``REQUESTS_CA_BUNDLE`` wins if both are set.

    Without either, returns ``True`` and httpx2 falls back to the OS trust store, so
    minimal images need a populated system CA store.
    """
    ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if ca_bundle:
        return ssl.create_default_context(cafile=ca_bundle)
    return True


def default_base_transport_factory(
    limits: Limits | None = None,
    verify: ssl.SSLContext | bool | None = None,
) -> BaseTransportFactory:
    """Build the standard network transport for a route.

    The only place an AsyncHTTPTransport is built, so limits and SSL verification apply
    the same way to direct and proxied routes.
    """
    resolved_verify = get_ssl_verify() if verify is None else verify

    def make_base_transport(proxy: str | None) -> AsyncBaseTransport:
        kwargs: dict[str, Any] = {"verify": resolved_verify}
        if limits is not None:
            kwargs["limits"] = limits
        if proxy is not None:
            kwargs["proxy"] = proxy
        return AsyncHTTPTransport(**kwargs)

    return make_base_transport


def fixed_base_transport_factory(
    transport: AsyncBaseTransport,
) -> BaseTransportFactory:
    """Serve every route from one already built transport.

    Proxy settings cannot reach a finished instance, so it answers direct and proxied
    routes alike, which is what a test double wants. Write your own factory if you need
    proxy-aware transports.
    """
    return lambda _proxy: transport


def _resolve_base_transport_factory(
    base_transport: AsyncBaseTransport | None,
    limits: Limits | None,
    make_base_transport: BaseTransportFactory | None,
) -> BaseTransportFactory:
    """Reduce the legacy base_transport/limits pair to a single factory."""
    if make_base_transport is not None:
        if base_transport is not None or limits is not None:
            raise ValueError(
                "make_base_transport already decides how every transport is built."
                " Drop base_transport and limits, and apply them inside the factory."
            )
        return make_base_transport
    if base_transport is not None:
        if limits is not None:
            warnings.warn(
                "limits are ignored when base_transport is given; size the transport"
                " you pass in instead. This will raise in 9.0.",
                DeprecationWarning,
                stacklevel=3,
            )
        return fixed_base_transport_factory(base_transport)
    return default_base_transport_factory(limits)


class CompositeTransportFactory:
    """Builds the wrapped transport stacks this package provides."""

    @classmethod
    def _create_common_transport_layers(  # noqa: PLR0913
        cls,
        config: CompositeConfig,
        base_transport: AsyncBaseTransport | None = None,
        limits: Limits | None = None,
        *,
        make_base_transport: BaseTransportFactory | None = None,
        proxy: str | None = None,
        budget: RateBudget | None = None,
    ):
        """Creates wrapped transports reused between different factory methods."""
        factory = _resolve_base_transport_factory(
            base_transport, limits, make_base_transport
        )
        ratelimiting_transport = AsyncRateLimitingTransport(
            config=config, transport=factory(proxy), budget=budget
        )
        return AsyncRetryTransport(config=config, transport=ratelimiting_transport)

    @classmethod
    def create_ratelimiting_retry_transport(  # noqa: PLR0913
        cls,
        config: CompositeConfig,
        base_transport: AsyncBaseTransport | None = None,
        limits: Limits | None = None,
        *,
        make_base_transport: BaseTransportFactory | None = None,
        proxy: str | None = None,
        budget: RateBudget | None = None,
    ) -> AsyncRetryTransport:
        """Build one route's stack: retry, wrapping rate limiting, wrapping a base transport.

        Prefer `get_composite_client`, which builds a whole client and shares one budget
        across its routes.

        `make_base_transport` is called with `proxy` to build the base transport.
        `base_transport` and `limits` are older sugar over it, and warn when combined
        because limits cannot reach a finished transport. Pass `budget` to share pacing.
        """
        return cls._create_common_transport_layers(
            config,
            base_transport=base_transport,
            limits=limits,
            make_base_transport=make_base_transport,
            proxy=proxy,
            budget=budget,
        )
