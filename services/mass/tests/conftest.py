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

"""Import session-scoped container fixtures and function-scoped client fixtures."""

from hexkit.providers.akafka.testutils import (  # noqa: F401
    get_persistent_kafka_fixture,
    kafka_container_fixture,
)
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    get_persistent_mongodb_fixture,
    mongodb_container_fixture,
)

from tests.fixtures.joint import (  # noqa: F401
    JointFixture,
    joint_fixture,
)

mongodb = get_persistent_mongodb_fixture()
kafka = get_persistent_kafka_fixture()
