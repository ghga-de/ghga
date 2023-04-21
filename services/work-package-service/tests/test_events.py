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

"""Test that the work package service consumes and processes events properly."""

from hexkit.providers.akafka.testutils import (  # noqa: F401 # pylint: disable=unused-import
    kafka_fixture,
)
from hexkit.providers.mongodb.testutils import (  # noqa: F401 # pylint: disable=unused-import
    mongodb_fixture,
)
from pytest import mark, raises

from wps.container import Container

from .fixtures import fixture_container  # noqa: F401 # pylint: disable=unused-import
from .fixtures.datasets import DATASET


@mark.asyncio
async def test_dataset_registration(container: Container):
    """Test the registration of a dataset announced as an event."""

    repository = await container.work_package_repository()
    dataset = await repository.get_dataset("some-dataset-id")

    assert dataset == DATASET

    with raises(repository.DatasetNotFoundError):
        await repository.get_dataset("another-dataset-id")
