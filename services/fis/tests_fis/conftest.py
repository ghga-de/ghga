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
"""Fixtures"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.jwt_helpers import generate_jwk
from hexkit.providers.akafka.testutils import (  # noqa: F401
    kafka_container_fixture,
    kafka_fixture,
)
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    mongodb_container_fixture,
    mongodb_fixture,
)
from jwcrypto.jwk import JWK

from fis.config import Config
from fis.inject import prepare_rest_app
from tests_fis.fixtures.config import get_config
from tests_fis.fixtures.joint import JointRig, joint_fixture, rig  # noqa: F401


@pytest.fixture()
def data_hub_aliases() -> list[str]:
    """A list of available data hubs for test cases"""
    return ["HUB1", "HUB2", "HUB3"]


@pytest.fixture()
def data_hub_jwks(data_hub_aliases: list[str]) -> dict[str, JWK]:
    """Returns a dictionary of data hubs and their JWKs"""
    return {hub: generate_jwk() for hub in data_hub_aliases}


@pytest.fixture(name="config")
def config_fixture(data_hub_jwks: dict[str, JWK]) -> Config:
    """Create a config instance with Data Hub auth keys"""
    data_hub_auth_keys: dict[str, str] = {
        hub: jwk.export_public() for hub, jwk in data_hub_jwks.items()
    }
    return get_config(data_hub_auth_keys=data_hub_auth_keys)


@pytest_asyncio.fixture()
async def rest_client(rig: JointRig) -> AsyncGenerator[AsyncTestClient]:  # noqa: F811
    """Produce a test client fitted with configured components"""
    async with prepare_rest_app(
        config=rig.config, core_override=rig.interrogation_handler
    ) as app:
        yield AsyncTestClient(app=app)
