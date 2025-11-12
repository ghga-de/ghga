# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from hishel import AsyncCacheTransport, AsyncInMemoryStorage, Controller
from httpx import AsyncBaseTransport, AsyncHTTPTransport, Limits

from .config import CompositeCacheConfig, CompositeConfig
from .ratelimiting import AsyncRateLimitingTransport
from .retry import AsyncRetryTransport


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
        base_transport = (
            base_transport or AsyncHTTPTransport(limits=limits)
            if limits
            else AsyncHTTPTransport()
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
        controller = Controller(
            cacheable_methods=config.client_cacheable_methods,
            cacheable_status_codes=config.client_cacheable_status_codes,
        )
        storage = AsyncInMemoryStorage(
            ttl=config.client_cache_ttl, capacity=config.client_cache_capacity
        )
        return AsyncCacheTransport(
            controller=controller, transport=retry_transport, storage=storage
        )
