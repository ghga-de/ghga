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

import logging
import os
import ssl
from collections.abc import Callable
from typing import Any

from httpx2 import AsyncBaseTransport, AsyncHTTPTransport, Limits

from .config import CompositeConfig
from .ratelimiting import AsyncRateLimitingTransport, RateBudget
from .retry import AsyncRetryTransport

BaseTransportFactory = Callable[[str | None], AsyncBaseTransport]

log = logging.getLogger(__name__)


def get_ssl_verify() -> ssl.SSLContext | bool:
    """Determine the SSL verification setting for outgoing transports.

    Honors the standard ``REQUESTS_CA_BUNDLE`` and ``SSL_CERT_FILE`` environment
    variables (the same ones respected by ``requests``, ``urllib3`` and boto3) so
    that deployments behind SSL-inspecting proxies or with self-signed/custom CA
    chains verify correctly. ``REQUESTS_CA_BUNDLE`` takes precedence.

    If either variable is set, an ``ssl.SSLContext`` loaded from the referenced CA
    bundle is returned. If neither is set, ``True`` is returned so that httpx2 keeps
    its default behavior: the OS trust store via ``truststore``, not certifi as in
    httpx 0.x. Minimal images therefore need a populated system CA store.
    """
    ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if ca_bundle:
        return ssl.create_default_context(cafile=ca_bundle)
    return True


def default_base_transport_factory(
    limits: Limits | None = None,
    verify: ssl.SSLContext | bool | None = None,
) -> BaseTransportFactory:
    """Build a factory producing the standard network transport for a route.

    Applies the same limits and SSL verification to direct and proxied routes.
    """
    resolved_verify = get_ssl_verify() if verify is None else verify

    def make_base_transport(proxy: str | None) -> AsyncBaseTransport:
        kwargs: dict[str, Any] = {"verify": resolved_verify}
        if limits:
            kwargs["limits"] = limits
        if proxy:
            kwargs["proxy"] = proxy
        return AsyncHTTPTransport(**kwargs)

    return make_base_transport


def fixed_base_transport_factory(
    transport: AsyncBaseTransport,
) -> BaseTransportFactory:
    """Serve every route from one already built transport.

    This will ignore proxy settings as they can't be applied to an already created instance.
    """
    return lambda _: transport


class CompositeTransportFactory:
    """Produces different flavors of httpx2.AsyncHTTPTransports and takes care of wrapping them in the correct order."""

    @classmethod
    def _create_common_transport_layers(
        cls,
        config: CompositeConfig,
        *,
        make_base_transport: BaseTransportFactory | None = None,
        proxy: str | None = None,
        budget: RateBudget | None = None,
    ):
        """Creates wrapped transports reused between different factory methods.

        If `make_base_transport` is not provided, a default factory using default
        limits is used.
        Passing `budget` paces requests across routes.
        """
        factory = make_base_transport or default_base_transport_factory()
        ratelimiting_transport = AsyncRateLimitingTransport(
            config=config, transport=factory(proxy), budget=budget
        )
        return AsyncRetryTransport(config=config, transport=ratelimiting_transport)

    @classmethod
    def create_ratelimiting_retry_transport(
        cls,
        config: CompositeConfig,
        *,
        make_base_transport: BaseTransportFactory | None = None,
        proxy: str | None = None,
        budget: RateBudget | None = None,
    ) -> AsyncRetryTransport:
        """Creates a retry transport, wrapping, in sequence, a rate limiting transport and a base transport.

        Pass `budget` to pace requests across routes of the same client.
        """
        return cls._create_common_transport_layers(
            config,
            make_base_transport=make_base_transport,
            proxy=proxy,
            budget=budget,
        )
