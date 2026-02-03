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

"""Tests for proxy handling functions."""

from collections.abc import Callable
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from hishel.httpx import AsyncCacheTransport

from ghga_service_commons.transports.config import CompositeCacheConfig, CompositeConfig
from ghga_service_commons.transports.proxy_handling import (
    cached_ratelimiting_retry_proxies,
    ratelimiting_retry_proxies,
)
from ghga_service_commons.transports.retry import AsyncRetryTransport

# Protocol keys used in proxy configuration
HTTP_PROTOCOL = "http://"
HTTPS_PROTOCOL = "https://"
ALL_PROTOCOL = "all://"

# Proxy URLs for each protocol
HTTP_PROXY_URL = "http://proxy.example.com:8080"
HTTPS_PROXY_URL = "https://secure-proxy.example.com:8443"
ALL_PROXY_URL = "http://fallback-proxy.example.com:8080"

# Request URLs for testing
HTTP_REQUEST_URL = "http://example.com/test"
HTTPS_REQUEST_URL = "https://secure.example.com/api"
ALL_REQUEST_URL = "ftp://files.example.com/data"

# Response content patterns
HTTP_PROTOCOL_RESPONSE = b'{"protocol": "http"}'
HTTPS_PROTOCOL_RESPONSE = b'{"protocol": "https"}'
ALL_PROTOCOL_RESPONSE = b'{"protocol": "fallback"}'

# Multi-protocol configuration
MULTI_PROXY_CONFIG = {
    HTTP_PROTOCOL: HTTP_PROXY_URL,
    HTTPS_PROTOCOL: HTTPS_PROXY_URL,
    ALL_PROTOCOL: ALL_PROXY_URL,
}


@pytest.mark.parametrize(
    "config_class,proxy_fn,expected_transport",
    [
        (CompositeConfig, ratelimiting_retry_proxies, AsyncRetryTransport),
        (
            CompositeCacheConfig,
            cached_ratelimiting_retry_proxies,
            AsyncCacheTransport,
        ),
    ],
)
@pytest.mark.parametrize(
    "protocol_key,proxy_url",
    [*MULTI_PROXY_CONFIG.items()],
)
def test_with_single_proxy(
    config_class: type[CompositeConfig | CompositeCacheConfig],
    proxy_fn: Callable,
    expected_transport: type[AsyncRetryTransport | AsyncCacheTransport],
    protocol_key: str,
    proxy_url: str,
):
    """Test that proxy is correctly configured for each protocol."""
    config = config_class()

    with patch(
        "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
        return_value={protocol_key: proxy_url},
    ):
        mounts = proxy_fn(config)

        assert protocol_key in mounts
        assert isinstance(mounts[protocol_key], expected_transport)


@pytest.mark.parametrize(
    "config_class,proxy_fn,expected_transport",
    [
        (CompositeConfig, ratelimiting_retry_proxies, AsyncRetryTransport),
        (
            CompositeCacheConfig,
            cached_ratelimiting_retry_proxies,
            AsyncCacheTransport,
        ),
    ],
)
def test_with_multiple_proxies(
    config_class: type[CompositeConfig | CompositeCacheConfig],
    proxy_fn: Callable,
    expected_transport: type[AsyncRetryTransport | AsyncCacheTransport],
):
    """Test that multiple proxy protocols are configured together."""
    config = config_class()

    with patch(
        "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
        return_value=MULTI_PROXY_CONFIG,
    ):
        mounts = proxy_fn(config)

        assert len(mounts) == 3
        assert HTTP_PROTOCOL in mounts
        assert HTTPS_PROTOCOL in mounts
        assert ALL_PROTOCOL in mounts
        assert all(
            isinstance(transport, expected_transport) for transport in mounts.values()
        )


@pytest.mark.parametrize(
    "config_class,proxy_fn",
    [
        (CompositeConfig, ratelimiting_retry_proxies),
        (CompositeCacheConfig, cached_ratelimiting_retry_proxies),
    ],
)
def test_with_no_proxies(
    config_class: type[CompositeConfig | CompositeCacheConfig],
    proxy_fn: Callable,
):
    """Test that empty dict is returned when no proxies are configured."""
    config = config_class()

    with patch(
        "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
        return_value={},
    ):
        mounts = proxy_fn(config)

        assert mounts == {}


@pytest.mark.parametrize(
    "config_class,proxy_fn",
    [
        (CompositeConfig, ratelimiting_retry_proxies),
        (CompositeCacheConfig, cached_ratelimiting_retry_proxies),
    ],
)
def test_filters_none_proxy_values(
    config_class: type[CompositeConfig | CompositeCacheConfig],
    proxy_fn: Callable,
):
    """Test that None proxy values are filtered out."""
    config = config_class()

    with patch(
        "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
        return_value={
            HTTP_PROTOCOL: HTTP_PROXY_URL,
            HTTPS_PROTOCOL: None,
            ALL_PROTOCOL: ALL_PROXY_URL,
        },
    ):
        mounts = proxy_fn(config)

        # The function should filter out None values
        assert len(mounts) == 2
        assert HTTP_PROTOCOL in mounts
        assert ALL_PROTOCOL in mounts
        assert HTTPS_PROTOCOL not in mounts


@pytest.mark.parametrize(
    "config_class,proxy_fn",
    [
        (CompositeConfig, ratelimiting_retry_proxies),
        (CompositeCacheConfig, cached_ratelimiting_retry_proxies),
    ],
)
@pytest.mark.parametrize(
    "protocol_key,proxy_url,request_url,expected_response",
    [
        (
            HTTP_PROTOCOL,
            HTTP_PROXY_URL,
            HTTP_REQUEST_URL,
            HTTP_PROTOCOL_RESPONSE,
        ),
        (
            HTTPS_PROTOCOL,
            HTTPS_PROXY_URL,
            HTTPS_REQUEST_URL,
            HTTPS_PROTOCOL_RESPONSE,
        ),
        (
            ALL_PROTOCOL,
            ALL_PROXY_URL,
            ALL_REQUEST_URL,
            ALL_PROTOCOL_RESPONSE,
        ),
    ],
)
@pytest.mark.asyncio
async def test_with_proxy_mount(
    config_class: type[CompositeConfig | CompositeCacheConfig],
    proxy_fn: Callable,
    protocol_key: str,
    proxy_url: str,
    request_url: str,
    expected_response: bytes,
):
    """Test that proxy mounts work with AsyncClient."""
    config = config_class()

    with patch(
        "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
        return_value={protocol_key: proxy_url},
    ):
        mounts = proxy_fn(config)

        mock_response = httpx.Response(
            status_code=200,
            content=expected_response,
        )

        with patch.object(
            mounts[protocol_key],
            "handle_async_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            async with httpx.AsyncClient(mounts=mounts) as client:
                response = await client.get(request_url)

                assert response.status_code == 200
                assert response.json() is not None

                transport = mounts[protocol_key]
                transport.handle_async_request.assert_called()
                # check the proxy base transports were wrapped
                assert isinstance(transport, (AsyncRetryTransport, AsyncCacheTransport))


@pytest.mark.parametrize(
    "config_class,proxy_fn",
    [
        (CompositeConfig, ratelimiting_retry_proxies),
        (CompositeCacheConfig, cached_ratelimiting_retry_proxies),
    ],
)
@pytest.mark.parametrize(
    "protocol_key,proxy_url,request_url,expected_response",
    [
        (
            HTTPS_PROTOCOL,
            HTTPS_PROXY_URL,
            HTTP_REQUEST_URL,
            HTTPS_PROTOCOL_RESPONSE,
        )
    ],
)
@pytest.mark.asyncio
async def test_not_hitting_proxy_mount(
    config_class: type[CompositeConfig | CompositeCacheConfig],
    proxy_fn: Callable,
    protocol_key: str,
    proxy_url: str,
    request_url: str,
    expected_response: bytes,
):
    """Test that proxy mounts are not used in AsyncClient if the URL protocol doesn't match."""
    config = config_class()

    with patch(
        "ghga_service_commons.transports.proxy_handling._utils.get_environment_proxies",
        return_value={protocol_key: proxy_url},
    ):
        mounts = proxy_fn(config)

        mock_response = httpx.Response(
            status_code=200,
            content=expected_response,
        )

        with patch.object(
            mounts[protocol_key],
            "handle_async_request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            async with httpx.AsyncClient(mounts=mounts) as client:
                await client.get(request_url)
                mounts[protocol_key].handle_async_request.assert_not_called()
