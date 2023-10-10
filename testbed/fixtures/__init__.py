# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from typing import NamedTuple

from hexkit.providers.testing.utils import get_event_loop
from pytest import fixture

from fixtures.auth import TokenGenerator, auth_fixture
from fixtures.config import Config
from fixtures.connector import ConnectorFixture, connector_fixture
from fixtures.dsk import DskFixture, dsk_fixture
from fixtures.file import batch_file_fixture, file_fixture
from fixtures.http import HttpClient, Response, http_fixture
from fixtures.kafka import KafkaFixture, kafka_fixture
from fixtures.mongo import MongoFixture, mongo_fixture
from fixtures.s3 import S3Fixture, s3_fixture
from fixtures.state import StateStorage, state_fixture

__all__ = [
    "auth_fixture",
    "config_fixture",
    "http_fixture",
    "kafka_fixture",
    "mongo_fixture",
    "s3_fixture",
    "joint_fixture",
    "batch_file_fixture",
    "file_fixture",
    "dsk_fixture",
    "connector_fixture",
    "state_fixture",
    "Config",
    "HttpClient",
    "JointFixture",
    "Response",
    "StateStorage",
]

event_loop = get_event_loop(scope="session")


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


@fixture(name="config", scope="session")  # pyright: ignore
def config_fixture() -> Config:
    """Get the testbed configuration."""
    return Config()  # pyright: ignore


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
) -> JointFixture:
    """A fixture that collects all fixtures for integration testing."""

    return JointFixture(config, http, kafka, mongo, s3, auth, dsk, connector, state)
