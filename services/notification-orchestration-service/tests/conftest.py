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
#
"""Test-suite-wide fixture declaration."""

import pytest_asyncio
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.protocols.dao import ResourceNotFoundError
from hexkit.providers.akafka.testutils import (  # noqa: F401
    kafka_container_fixture,
    kafka_fixture,
)
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    mongodb_container_fixture,
    mongodb_fixture,
)

from tests.fixtures.joint import JointFixture, joint_fixture  # noqa: F401

TEST_USER = event_schemas.User(
    user_id="test_id",
    name="test user",
    title=event_schemas.AcademicTitle.DR,
    email="test@test.abc",
)


@pytest_asyncio.fixture(autouse=True)
async def insert_test_data(joint_fixture: JointFixture):  # noqa: F811
    """Fixture that inserts TEST_USER into the database and deletes it after the tests
    are done.

    The ID-containing user is assigned as an attribute to the joint_fixture as well so
    the ID is easily accessible to tests.
    """
    await joint_fixture.user_dao.insert(TEST_USER)
    yield
    try:
        await joint_fixture.user_dao.delete(TEST_USER.user_id)
    except ResourceNotFoundError:
        pass
