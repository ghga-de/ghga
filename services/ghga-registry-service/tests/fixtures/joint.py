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

"""Bundle different test fixtures into one fixture."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest_asyncio
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.auth.ghga import AuthConfig
from ghga_service_commons.utils import jwt_helpers
from hexkit.providers.akafka.testutils import KafkaFixture
from hexkit.providers.mongodb.testutils import MongoDbFixture
from jwcrypto.jwk import JWK

from rs.config import Config
from rs.inject import prepare_core, prepare_rest_app
from rs.ports.inbound.files import FileControllerPort
from tests.fixtures.config import get_config


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    controller: FileControllerPort
    kafka: KafkaFixture
    mongodb: MongoDbFixture
    rest_client: AsyncTestClient
    uos_jwk: JWK


@pytest_asyncio.fixture(scope="function")
async def joint_fixture(
    mongodb: MongoDbFixture,
    kafka: KafkaFixture,
) -> AsyncGenerator[JointFixture]:
    """A fixture that embeds all other fixtures for API-level integration testing.

    **Do not call directly** Instead, use get_joint_fixture().
    """
    uos_jwk = jwt_helpers.generate_jwk()
    uos_auth_key = uos_jwk.export(private_key=False)
    uos_cfg = AuthConfig(auth_key=uos_auth_key, auth_check_claims={})

    # merge configs from different sources with the default one
    config = get_config(sources=[mongodb.config, kafka.config], uos_auth_config=uos_cfg)

    # Knit together the components into the joint fixture
    async with (
        prepare_core(config=config) as controller,
        prepare_rest_app(config=config, core_override=controller) as app,
        AsyncTestClient(app=app) as rest_client,
    ):
        yield JointFixture(
            config=config,
            controller=controller,
            kafka=kafka,
            mongodb=mongodb,
            rest_client=rest_client,
            uos_jwk=uos_jwk,
        )
