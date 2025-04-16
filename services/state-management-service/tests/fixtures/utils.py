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

"""Utils for Fixture handling."""

from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock

from ghga_service_commons.api.testing import AsyncTestClient

from sms.config import Config
from sms.inject import prepare_rest_app
from sms.ports.inbound.docs_handler import DocsHandlerPort
from sms.ports.inbound.events_handler import EventsHandlerPort
from sms.ports.inbound.objects_handler import ObjectsHandlerPort
from sms.ports.inbound.secrets_handler import SecretsHandlerPort

BASE_DIR = Path(__file__).parent.resolve()

VALID_BEARER_TOKEN = "Bearer 43fadc91-b98f-4925-bd31-1b054b13dc55"


@asynccontextmanager
async def get_rest_client(
    config: Config,
    *,
    docs_handler_override: DocsHandlerPort | None = None,
    objects_handler_override: ObjectsHandlerPort | None = None,
    events_handler_override: EventsHandlerPort | None = None,
    secrets_handler_override: SecretsHandlerPort | None = None,
):
    """Prepare a REST API client for testing."""
    async with prepare_rest_app(
        config=config,
        docs_handler_override=docs_handler_override,
        objects_handler_override=objects_handler_override,
        events_handler_override=events_handler_override,
        secrets_handler_override=secrets_handler_override,
    ) as app:
        async with AsyncTestClient(app) as client:
            yield client


@asynccontextmanager
async def get_rest_client_with_mocks(
    config: Config,
    *,
    docs_handler_override: DocsHandlerPort | None = None,
    objects_handler_override: ObjectsHandlerPort | None = None,
    events_handler_override: EventsHandlerPort | None = None,
    secrets_handler_override: SecretsHandlerPort | None = None,
):
    """Prepare a REST client with the dependencies mocked by default

    This negates the need to explicitly mock unused dependencies in each test.
    """
    docs_handler = docs_handler_override or AsyncMock()
    objects_handler = objects_handler_override or AsyncMock()
    events_handler = events_handler_override or AsyncMock()
    secrets_handler = secrets_handler_override or AsyncMock()
    async with get_rest_client(
        config,
        docs_handler_override=docs_handler,
        objects_handler_override=objects_handler,
        events_handler_override=events_handler,
        secrets_handler_override=secrets_handler,
    ) as client:
        yield client
