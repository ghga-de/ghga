# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Fixtures for the inter service integration tests"""

import asyncio
from typing import NamedTuple

from pytest import fixture

from fixtures.auth import TokenGenerator, auth_fixture
from fixtures.config import Config
from fixtures.connector import ConnectorFixture, connector_fixture
from fixtures.dsk import DskFixture, dsk_fixture
from fixtures.file import file_fixture
from fixtures.http_client import HttpClient, Response, http_fixture
from fixtures.iva import IVAFixture, iva_fixture
from fixtures.kafka import KafkaFixture, kafka_fixture
from fixtures.mongo import MongoFixture, mongo_fixture
from fixtures.s3 import S3Fixture, s3_fixture
from fixtures.state import StateStorage, state_fixture
from fixtures.state_manager import StateManager, state_manager_fixture
from fixtures.vault import VaultFixture, vault_fixture

__all__ = [
    "auth_fixture",
    "config_fixture",
    "http_fixture",
    "kafka_fixture",
    "mongo_fixture",
    "s3_fixture",
    "joint_fixture",
    "file_fixture",
    "dsk_fixture",
    "connector_fixture",
    "state_fixture",
    "state_manager_fixture",
    "Config",
    "HttpClient",
    "JointFixture",
    "Response",
    "StateStorage",
    "StateManager",
    "vault_fixture",
    "iva_fixture",
]


def event_loop_fixture():
    """Event loop fixture for when an event loop is needed beyond function scope."""
    loop = asyncio.get_running_loop()
    yield loop
    loop.close()


event_loop = fixture(fixture_function=event_loop_fixture, scope="session")


class JointFixture(NamedTuple):
    """Collection of fixtures returned by `joint_fixture`."""

    config: Config
    http: HttpClient
    kafka: KafkaFixture
    mongo: MongoFixture
    s3: S3Fixture
    auth: TokenGenerator
    dsk: DskFixture
    connector: ConnectorFixture
    state: StateStorage
    vault: VaultFixture
    iva: IVAFixture


@fixture(name="config", scope="session")  # pyright: ignore
def config_fixture() -> Config:
    """Get the testbed configuration."""
    return Config()  # type: ignore


# pylint: disable=redefined-outer-name
@fixture(name="fixtures", scope="session")
def joint_fixture(
    config: Config,
    http: HttpClient,
    kafka: KafkaFixture,
    mongo: MongoFixture,
    s3: S3Fixture,
    auth: TokenGenerator,
    dsk: DskFixture,
    connector: ConnectorFixture,
    state: StateStorage,
    vault: VaultFixture,
    iva: IVAFixture,
) -> JointFixture:
    """A fixture that collects all fixtures for integration testing."""

    return JointFixture(
        config,
        http,
        kafka,
        mongo,
        s3,
        auth,
        dsk,
        connector,
        state,
        vault,
        iva,
    )
