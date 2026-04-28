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

"""Dependency injection module"""

__all__ = []

from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager, nullcontext

from fastapi import FastAPI

from ekss.adapters.inbound.fastapi_ import dummies
from ekss.adapters.inbound.fastapi_.configure import get_configured_app
from ekss.adapters.outbound.vault import VaultClient
from ekss.config import Config
from ekss.core.secrets import SecretsHandler
from ekss.ports.inbound.secrets import SecretsHandlerPort


# Note that the core preparation functions are sync, not async, unlike most ghga services
@contextmanager
def prepare_core(*, config: Config) -> Generator[SecretsHandlerPort]:
    """Constructs and initializes all core components and their outbound dependencies.

    The _override parameters can be used to override the default dependencies.
    """
    vault_client = VaultClient(config=config)
    yield SecretsHandler(config=config, vault_client=vault_client)


def prepare_core_with_override(
    *,
    config: Config,
    secrets_handler_override: SecretsHandlerPort | None = None,
):
    """Resolve the secrets_handler context manager based on config and override (if any)."""
    return (
        nullcontext(secrets_handler_override)
        if secrets_handler_override
        else prepare_core(config=config)
    )


@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
    secrets_handler_override: SecretsHandlerPort | None = None,
) -> AsyncGenerator[FastAPI]:
    """Construct and initialize an REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the override parameter.
    """
    app = get_configured_app(config=config)

    with prepare_core_with_override(
        config=config, secrets_handler_override=secrets_handler_override
    ) as secrets_handler:
        app.dependency_overrides[dummies.secrets_handler_port] = lambda: secrets_handler
        yield app
