# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Setup for testing the access request service."""

import pytest
from hexkit.providers.akafka.testutils import get_kafka_fixture
from hexkit.providers.mongodb.testutils import get_mongodb_fixture

from .fixtures import JointFixture, get_joint_fixture


@pytest.fixture(autouse=True)
def reset_state(joint_fixture: JointFixture):
    """Clear joint_fixture state before tests.

    This is a function-level fixture because it needs to run in each test.
    """
    joint_fixture.mongodb.empty_collections()


kafka_fixture = get_kafka_fixture("session")
mongodb_fixture = get_mongodb_fixture("session")
joint_fixture = get_joint_fixture("session")
