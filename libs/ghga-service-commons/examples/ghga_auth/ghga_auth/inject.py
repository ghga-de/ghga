# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Dependency injection logic"""

from __future__ import annotations

from contextlib import asynccontextmanager

from ghga_auth import dummies
from ghga_auth.config import Config
from ghga_auth.router_config import get_configured_app
from ghga_service_commons.auth.context import AuthContextProtocol
from ghga_service_commons.auth.ghga import AuthContext, GHGAAuthContextProvider
from ghga_service_commons.utils.context import asyncnullcontext


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    auth_provider_override: AuthContextProtocol[AuthContext] | None = None,
):
    """Construct and initialize an REST API app along with all its dependencies.

    By default, the core dependencies are automatically prepared but you can also
    provide them using the auth_provider_override parameter.
    """
    app = get_configured_app(config=config)

    async with (
        asyncnullcontext(auth_provider_override)
        if auth_provider_override
        else GHGAAuthContextProvider.construct(
            config=config,
            context_class=AuthContext,
        )
    ) as auth_provider:
        app.dependency_overrides[dummies.auth_provider_dummy] = lambda: auth_provider
        yield app
