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
"""Set up session-scope fixtures for tests."""

import pytest
from hexkit.correlation import correlation_id_var, new_correlation_id
from hexkit.providers.akafka.testutils import (
    kafka_container_fixture,  # noqa: F401
    kafka_fixture,  # noqa: F401
)
from hexkit.providers.mongodb.testutils import (
    mongodb_container_fixture,  # noqa: F401
    mongodb_fixture,  # noqa: F401
)
from hexkit.providers.mongokafka.testutils import MongoKafkaFixture  # noqa: F401
from hexkit.providers.s3.testutils import (  # noqa: F401
    FederatedS3Fixture,
    federated_s3_fixture,
    s3_multi_container_fixture,
)

from tests_ifrs.fixtures.joint import (  # noqa: F401
    DOWNLOAD_BUCKET,
    INTERROGATION_BUCKET,
    PERMANENT_BUCKET,
    STORAGE_ALIASES,
    JointFixture,
    joint_fixture,
)


@pytest.fixture(autouse=True)
def use_correlation_id():
    """Provides a new correlation ID for each test case."""
    correlation_id = new_correlation_id()
    token = correlation_id_var.set(correlation_id)
    yield
    correlation_id_var.reset(token)


@pytest.fixture(scope="session")
def storage_aliases():
    """Defines the names of the storage aliases for the federated s3 storage.

    This fixture is expected by hexkit.
    """
    return STORAGE_ALIASES
