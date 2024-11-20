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
"""Import necessary test fixtures."""

import pytest
from hexkit.providers.akafka.testutils import (  # noqa: F401
    kafka_container_fixture,
    kafka_fixture,
)
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    mongodb_container_fixture,
    mongodb_fixture,
)
from hexkit.providers.s3.testutils import (  # noqa: F401
    federated_s3_fixture,
    s3_multi_container_fixture,
)

from tests.fixtures.config import DEFAULT_TEST_CONFIG


@pytest.fixture(scope="session")
def storage_aliases():
    """Supplies the aliases to the federated S3 fixture.

    This tells it how many S3 storages to spin up and what names to associate with them.
    """
    return [alias for alias in DEFAULT_TEST_CONFIG.object_storages]
