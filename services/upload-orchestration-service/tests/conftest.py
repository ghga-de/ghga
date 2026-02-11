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
"""Set up session-scope fixtures for tests."""

from collections.abc import AsyncGenerator

import httpx
import pytest
import pytest_asyncio
from ghga_service_commons.utils import jwt_helpers
from hexkit.correlation import set_new_correlation_id
from hexkit.providers.akafka.testutils import (  # noqa: F401
    kafka_container_fixture,
    kafka_fixture,
)
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    mongodb_container_fixture,
    mongodb_fixture,
)
from hexkit.providers.s3.testutils import (  # noqa: F401
    s3_container_fixture,
    s3_fixture,
)

from tests.fixtures import ConfigFixture
from tests.fixtures.config import get_config
from tests.fixtures.joint import joint_fixture  # noqa: F401


@pytest.fixture(name="config")
def config_fixture() -> ConfigFixture:
    """Generate config from test yaml along with an auth key and JWK"""
    jwk = jwt_helpers.generate_jwk()
    auth_key = jwk.export(private_key=False)
    signing_key = jwt_helpers.generate_jwk().export_private()
    config = get_config(auth_key=auth_key, work_order_signing_key=signing_key)
    return ConfigFixture(config=config, jwk=jwk)


@pytest_asyncio.fixture(autouse=True)
async def cid_fixture():  # noqa: D103
    async with set_new_correlation_id() as cid:
        yield cid


@pytest_asyncio.fixture()
async def httpx_client() -> AsyncGenerator[httpx.AsyncClient]:
    """Yields an AsyncClient"""
    async with httpx.AsyncClient() as client:
        yield client
