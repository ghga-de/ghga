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
    """Build a client whose own transport and proxy mounts use the same stack.

    This is the normal way to use this package. Like httpx2 it builds a default transport
    plus one mount per proxy environment variable, but each one is retry wrapping rate
    limiting wrapping a base transport. Mounts still win for the URLs they claim.

    `limits` size the standard base transport. Supply `make_base_transport` instead to
    build your own per route and size it yourself; the two are mutually exclusive. Every
    route shares one `RateBudget`, so the configured rate applies to the whole client.

    Extra keyword arguments go to `httpx2.AsyncClient`.
    """
    if limits is not None and make_base_transport is not None:
        raise ValueError(
            "limits size the default base transport. Pass make_base_transport on its"
            " own and apply limits inside it."
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
