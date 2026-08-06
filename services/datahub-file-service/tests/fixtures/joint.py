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

"""Join the functionality of all fixtures for API-level integration testing."""

__all__ = ["JointFixture", "joint_fixture"]

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from functools import partial
from unittest.mock import patch

import pytest_asyncio
from hexkit.providers.s3.testutils import S3Fixture

from dhfs.config import Config
from dhfs.inject import prepare_interrogation_bucket_cleaner, prepare_interrogator
from dhfs.ports.outbound.cleaner import S3CleanerPort
from dhfs.ports.outbound.interrogator import InterrogatorPort
from tests.fixtures.central_api import CentralApiMock, get_mocked_httpx_client


@dataclass
class JointFixture:
    """Returned by the `joint_fixture`."""

    config: Config
    s3_cleaner: S3CleanerPort
    interrogator: InterrogatorPort
    s3: S3Fixture
    central_api: CentralApiMock


@pytest_asyncio.fixture(scope="function")
async def joint_fixture(s3: S3Fixture, config: Config) -> AsyncGenerator[JointFixture]:
    """A fixture that embeds all other fixtures for API-level integration testing."""
    # Patch the config so the URL/credentials point to the actual S3 testcontainers
    _patched_config = config.model_dump()
    _patched_config.update(s3.config.model_dump())
    patched_config = Config(**_patched_config)

    # Route Central API calls to the mock, but let S3 calls reach the testcontainer
    central_api = CentralApiMock(config=patched_config, passthrough=True)
    mocked_client_factory = partial(get_mocked_httpx_client, central_api=central_api)

    # Assemble joint fixture with config injection
    with patch("dhfs.inject.get_configured_httpx_client", mocked_client_factory):
        async with (
            prepare_interrogation_bucket_cleaner(config=patched_config) as s3_cleaner,
            prepare_interrogator(config=patched_config) as interrogator,
        ):
            yield JointFixture(
                config=patched_config,
                s3_cleaner=s3_cleaner,
                interrogator=interrogator,
                s3=s3,
                central_api=central_api,
            )
