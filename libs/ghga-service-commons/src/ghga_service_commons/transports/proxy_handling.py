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
This module provides custom proxy handling. httpx2 gives a custom transport precedence over
the proxies it reads from the environment, but custom transports + proxy are a valid use case
that need some custom logic around this default.

Env proxies are parsed by default, but can be disabled using `trust_env=False`.
Hosts excluded via NO_PROXY are kept as `None` mounts, which tells httpx2 to connect
directly to them.
"""

from httpx2 import AsyncBaseTransport, _utils

from .config import CompositeConfig
from .factory import (
    BaseTransportFactory,
    CompositeTransportFactory,
    default_base_transport_factory,
)
from .ratelimiting import RateBudget


def ratelimiting_retry_proxies(
    config: CompositeConfig,
    *,
    make_base_transport: BaseTransportFactory | None = None,
    budget: RateBudget | None = None,
    trust_env: bool = True,
) -> dict[str, AsyncBaseTransport | None]:
    """Setup proxies from env for ratelimiting retry transport.

    The returned dictionary needs to be provided as `mounts` to the client.
    Pass `budget` to enable request pacing, or `trust_env=False` to ignore the
    environment for proxies and return no mounts.
    If a `budget` is provided, it's shared between mounts.
    """
    if not trust_env:
        return {}

    factory = make_base_transport or default_base_transport_factory()
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

    This can potentially break without any notice and it's a tradeoff between
    accepting that and maintaining a separate copy of the code, that could
    drift and might cause unexpected behavior.
    """
    return _utils.get_environment_proxies()
