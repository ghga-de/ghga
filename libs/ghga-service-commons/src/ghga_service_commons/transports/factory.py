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

"""Provides factories for different flavors of httpx.AsyncHTTPTransport."""

import os
import ssl

from hishel import AsyncSqliteStorage, FilterPolicy
from hishel.httpx import AsyncCacheTransport
from httpx import AsyncBaseTransport, AsyncHTTPTransport, Limits

from .config import CompositeCacheConfig, CompositeConfig
from .ratelimiting import AsyncRateLimitingTransport
from .retry import AsyncRetryTransport


def get_ssl_verify() -> ssl.SSLContext | bool:
    """Determine the SSL verification setting for outgoing transports.

    Honors the standard ``REQUESTS_CA_BUNDLE`` and ``SSL_CERT_FILE`` environment
    variables (the same ones respected by ``requests``, ``urllib3`` and boto3) so
    that deployments behind SSL-inspecting proxies or with self-signed/custom CA
    chains verify correctly. ``REQUESTS_CA_BUNDLE`` takes precedence.

    If either variable is set, an ``ssl.SSLContext`` loaded from the referenced CA
    bundle is returned. If neither is set, ``True`` is returned so that httpx keeps
    its default behavior (certifi's bundled root certificates).
    """
    ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if ca_bundle:
        return ssl.create_default_context(cafile=ca_bundle)
    return True


class CompositeTransportFactory:
    """Produces different flavors of httpx.AsyncHTTPTransports and takes care of wrapping them in the correct order."""

    @classmethod
    def _create_common_transport_layers(
        cls,
        config: CompositeConfig,
        base_transport: AsyncBaseTransport | None = None,
        limits: Limits | None = None,
    ):
        """Creates wrapped transports reused between different factory methods.

        If provided, limits are applied to the AsyncHTTPTransport instance this method creates.
        If provided, a custom base_transport class is used and any limits are ignored.
        Those have to be provided directly to the custom base_transport passed into this method.
        """
        verify = get_ssl_verify()
        base_transport = base_transport or (
            AsyncHTTPTransport(limits=limits, verify=verify)
            if limits
            else AsyncHTTPTransport(verify=verify)
        )
        ratelimiting_transport = AsyncRateLimitingTransport(
            config=config, transport=base_transport
        )
        retry_transport = AsyncRetryTransport(
            config=config, transport=ratelimiting_transport
        )
        return retry_transport

    @classmethod
    def create_ratelimiting_retry_transport(
        cls,
        config: CompositeConfig,
        base_transport: AsyncBaseTransport | None = None,
        limits: Limits | None = None,
    ) -> AsyncRetryTransport:
        """Creates a retry transport, wrapping, in sequence, a rate limiting transport and AsyncHTTPTransport.

        If provided, limits are applied to the wrapped AsyncHTTPTransport instance.
        If provided, a custom base_transport class is used and any limits are ignored.
        Those have to be provided directly to the custom base_transport passed into this method.
        """
        return cls._create_common_transport_layers(
            config, base_transport=base_transport, limits=limits
        )

    @classmethod
    def create_cached_ratelimiting_retry_transport(
        cls,
        config: CompositeCacheConfig,
        base_transport: AsyncBaseTransport | None = None,
        limits: Limits | None = None,
    ) -> AsyncCacheTransport:
        """Creates a cache transport, wrapping, in sequence, a retry, rate limiting transport and AsyncHTTPTransport.

        If provided, limits are applied to the wrapped AsyncHTTPTransport instance.
        If provided, a custom base_transport class is used and any limits are ignored.
        Those have to be provided directly to the custom base_transport passed into this method.
        """
        retry_transport = cls._create_common_transport_layers(
            config, base_transport=base_transport, limits=limits
        )
        policy = FilterPolicy()
        storage = AsyncSqliteStorage(default_ttl=config.client_cache_ttl)
        return AsyncCacheTransport(
            next_transport=retry_transport,
            storage=storage,
            policy=policy,
        )
