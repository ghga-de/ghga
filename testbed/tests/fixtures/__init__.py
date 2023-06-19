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

from pytest import fixture

from src.config import Config
from tests.fixtures.akafka import KafkaFixture, kafka_fixture
from tests.fixtures.auth import TokenGenerator, auth_fixture
from tests.fixtures.mongodb import MongoDbFixture, mongodb_fixture
from tests.fixtures.s3 import S3Fixture, s3_fixture

__all__ = [
    "auth_fixture",
    "config_fixture",
    "kafka_fixture",
    "mongodb_fixture",
    "s3_fixture",
    "joint_fixture",
]


class JointFixture(NamedTuple):
    """Collection of fixtures returned by `joint_fixture`."""

    config: Config
    kafka: KafkaFixture
    mongodb: MongoDbFixture
    s3: S3Fixture
    auth: TokenGenerator


@fixture(name="config")  # pyright: ignore
def config_fixture() -> Config:
    """Get the testbed configuration."""
    return Config()  # pyright: ignore


# pylint: disable=redefined-outer-name
@fixture(name="fixtures")
def joint_fixture(
    config: Config,
    kafka_fixture: KafkaFixture,
    mongodb_fixture: MongoDbFixture,
    s3_fixture: S3Fixture,
    auth_fixture: TokenGenerator,
) -> JointFixture:
    """A fixture that collects all fixtures for integration testing."""

    return JointFixture(
        config, kafka_fixture, mongodb_fixture, s3_fixture, auth_fixture
    )
