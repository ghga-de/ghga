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
"""Builds proxy mounts that use this package's transport stack.

httpx2 mounts one transport per proxy environment variable, and mounts win over the
client's own transport. This does the same, but with our stack in each mount, so a
proxied route behaves like the direct one. NO_PROXY hosts stay as `None` mounts, which
tells httpx2 to connect directly for them.
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
    """Build the `mounts` map for a client, one stack per proxy route.

    Prefer `get_composite_client`, which pairs this with a matching transport for the
    direct route. Used directly, pass the result as `mounts` to the client.

    Each mount differs from the direct route only by the proxy its base transport uses.
    Pass `budget` to share pacing with the direct route, or `trust_env=False` to ignore
    the environment.
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
    """Parse proxy environment variables into mount patterns and proxy URLs.

    Hosts excluded by NO_PROXY map to `None`.

    `httpx2._utils.get_environment_proxies` is private and may disappear on any httpx2
    release. That risk is accepted rather than pinned around; replacing it here would be
    around thirty lines.
    """
    return _utils.get_environment_proxies()
