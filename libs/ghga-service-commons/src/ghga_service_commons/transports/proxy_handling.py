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
This module provides custom proxy handling. httpx2 gives a custom transport precedence
over the proxies it reads from the environment, so the proxy mounts have to be built
here instead. Env proxies are parsed by default; pass `trust_env=False` to skip them.

Hosts excluded via NO_PROXY are kept as `None` mounts, which tells httpx2 to connect
directly for them. Wildcard and CIDR NO_PROXY entries then follow httpx2's mount pattern
matching rather than its own NO_PROXY logic, which supplying `mounts` bypasses entirely.
"""

from httpx2 import AsyncBaseTransport, Limits, _utils

from .config import CompositeConfig
from .factory import (
    BaseTransportFactory,
    CompositeTransportFactory,
    _resolve_base_transport_factory,
)
from .ratelimiting import RateBudget


def ratelimiting_retry_proxies(
    config: CompositeConfig,
    limits: Limits | None = None,
    *,
    make_base_transport: BaseTransportFactory | None = None,
    budget: RateBudget | None = None,
    trust_env: bool = True,
) -> dict[str, AsyncBaseTransport | None]:
    """Setup proxies from env for ratelimiting retry transport.

    The returned dictionary needs to be provided as `mounts` to the client. Each mount
    is the same stack as the direct route, differing only by the proxy its base transport
    uses. Pass `budget` to share request pacing with the direct route, or
    `trust_env=False` to ignore the environment and return no mounts.
    """
    if not trust_env:
        return {}

    factory = _resolve_base_transport_factory(None, limits, make_base_transport)
    return {
        key: None
        if url is None
        else CompositeTransportFactory.create_ratelimiting_retry_transport(
            config=config, make_base_transport=factory, proxy=url, budget=budget
        )
        for key, url in _get_proxy_urls_from_env().items()
    }


def _get_proxy_urls_from_env() -> dict[str, str | None]:
    """Use httpx2 internals to correctly parse proxy environment variables.

    Covers the http, https and all proxy settings. NO_PROXY hosts come back with a
    ``None`` url, which is passed through so the caller can keep them as direct mounts.

    ``httpx2._utils.get_environment_proxies`` is private and may disappear on any httpx2
    release.
    """
    return _utils.get_environment_proxies()
