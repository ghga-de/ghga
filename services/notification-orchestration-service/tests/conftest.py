# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from hexkit.providers.akafka.testutils import get_kafka_fixture
from hexkit.providers.mongodb.testutils import get_mongodb_fixture

from nos.core.models import AcademicTitle, User
from tests.fixtures.joint import JointFixture, get_joint_fixture

mongodb_fixture = get_mongodb_fixture(scope="module")
kafka_fixture = get_kafka_fixture(scope="module")
joint_fixture = get_joint_fixture(scope="module")
TEST_USER = User(
    id="test", name="test user", title=AcademicTitle.DR, email="test@test.abc"
)


@pytest_asyncio.fixture(autouse=True, scope="module")
async def insert_test_data(joint_fixture: JointFixture):
    """Fixture that inserts TEST_USER into the database and deletes it after the tests
    are done.

    The ID-containing user is assigned as an attribute to the joint_fixture as well so
    the ID is easily accessible to tests.
    """
    await joint_fixture.user_dao.insert(TEST_USER)
    yield
    await joint_fixture.user_dao.delete(id_=TEST_USER.id)
