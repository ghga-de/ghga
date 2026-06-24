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
"""
This module provides custom proxy handling, as the way httpx setups the client, there is
an order of precedence which necessitates manual setup for proxies if a custom transport
is provided.

For now this logic is simplified, i.e. this is not in sync with `trust_env` on the
client and will parse env proxies unconditionally.
If you don't want to trust the env, don't use the functions from this module.

NO_PROXY is now respected: hosts excluded from proxying via NO_PROXY are kept as
`None` mounts, which tells httpx to connect directly for them. Note that wildcard and
CIDR NO_PROXY entries behave according to httpx's mount pattern matching rather than
httpx's own NO_PROXY logic (which is bypassed entirely once `mounts` are supplied).
This is a pre-existing limitation of routing through `mounts` and is not introduced
by this handling.
"""

from httpx import AsyncBaseTransport, AsyncHTTPTransport, Limits, _utils

from .config import CompositeCacheConfig, CompositeConfig
from .factory import CompositeTransportFactory, get_ssl_verify


def cached_ratelimiting_retry_proxies(
    config: CompositeCacheConfig,
    limits: Limits | None = None,
):
    """Setup proxies from env for cached ratelimiting retry transport.

    The returned dictionary needs to be provided as `mounts` to the client.
    """
    mounts: dict[str, AsyncBaseTransport | None] = dict()
    for key, transport in _get_base_proxies_from_env().items():
        if transport is None:
            # NO_PROXY host: keep None so httpx connects directly for this host.
            mounts[key] = None
            continue
        mounts[key] = (
            CompositeTransportFactory.create_cached_ratelimiting_retry_transport(
                config=config, base_transport=transport, limits=limits
            )
        )
    return mounts


def ratelimiting_retry_proxies(
    config: CompositeConfig,
    limits: Limits | None = None,
):
    """Setup proxies from env for ratelimiting retry transport.

    The returned dictionary needs to be provided as `mounts` to the client.
    """
    mounts: dict[str, AsyncBaseTransport | None] = dict()
    for key, transport in _get_base_proxies_from_env().items():
        if transport is None:
            # NO_PROXY host: keep None so httpx connects directly for this host.
            mounts[key] = None
            continue
        mounts[key] = CompositeTransportFactory.create_ratelimiting_retry_transport(
            config=config, base_transport=transport, limits=limits
        )
    return mounts


def _get_base_proxies_from_env() -> dict[str, AsyncHTTPTransport | None]:
    """Use httpx internals to correctly parse proxy environment variables.

    This will populate http, https and all proxy settings and create transports
    based on those proxy strings.

    NO_PROXY hosts are returned by httpx with a ``None`` url; these are preserved as
    ``None`` so that NO_PROXY is respected (httpx connects directly for them) instead
    of being silently routed through a proxy.
    """
    verify = get_ssl_verify()
    return {
        key: None if url is None else (AsyncHTTPTransport(proxy=url, verify=verify))
        for key, url in _utils.get_environment_proxies().items()
    }
