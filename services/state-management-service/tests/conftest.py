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

from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from hexkit.custom_types import PytestScope
from hexkit.providers.akafka.testutils import (  # noqa: F401
    kafka_container_fixture,
    kafka_fixture,
)
from hexkit.providers.mongodb.testutils import (  # noqa: F401
    mongodb_container_fixture,
    mongodb_fixture,
)
from hexkit.providers.s3 import S3ObjectStorage
from hexkit.providers.s3.testutils import (
    S3ContainerFixture,
    S3Fixture,
    temp_file_object,
)

from sms.config import Config
from tests.fixtures.config import get_config


# Move the federation fixtures to hexkit if deemed useful
class FederatedS3Fixture:
    """Fixture containing multiple S3 fixtures to simulate federated storage."""

    def __init__(self, storages: dict[str, S3Fixture]):
        self.nodes = storages

    def get_patched_config(self, *, config: Config):
        """Update a Config instance so the object storage credentials point to the
        respective S3Fixtures.
        """
        config_vals = config.model_dump()
        for alias in config.object_storages:
            node_config = self.nodes[alias].config.model_dump()
            config_vals["object_storages"][alias]["credentials"] = node_config
        return Config(**config_vals)

    async def populate_dummy_items(self, alias: str, buckets: dict[str, list[str]]):
        """Convenience function to populate a specific S3Fixture.

        The `buckets` arg is a dictionary with bucket names as keys and lists of objects
        as values. The buckets can be empty, and the objects are created with a size of
        1 byte. This function might be modified or removed in the hexkit version.
        """
        if alias not in self.nodes:
            # This would indicate some kind of mismatch between config and fixture
            raise RuntimeError(f"Alias '{alias}' not found in the federated S3 fixture")
        storage = self.nodes[alias]
        # Populate the buckets so even empty buckets are established
        await storage.populate_buckets([bucket for bucket in buckets])
        for bucket, objects in buckets.items():
            for object in objects:
                with temp_file_object(bucket, object, 1) as file:
                    await storage.populate_file_objects([file])


class MultiS3ContainerFixture:
    """Fixture for managing multiple running S3 test containers in order to mimic
    multiple object storages.

    Without this fixture, separate S3Fixture instances would access the same
    underlying storage resources.
    """

    def __init__(self, s3_containers: dict[str, S3ContainerFixture]):
        self.s3_containers = s3_containers

    def __enter__(self):
        """Enter the context manager and start the S3 containers."""
        for container in self.s3_containers.values():
            container.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and clean up the S3 containers."""
        for container in self.s3_containers.values():
            container.__exit__(exc_type, exc_val, exc_tb)


def _multi_s3_container_fixture() -> Generator[MultiS3ContainerFixture, None, None]:
    """Fixture function for getting multiple running S3 test containers."""
    config = get_config()
    s3_containers = {
        name: S3ContainerFixture(name=name) for name in config.object_storages
    }
    with MultiS3ContainerFixture(s3_containers) as multi_s3_container:
        yield multi_s3_container


def get_multi_s3_container_fixture():
    """Get a fixture containing multiple LocalStack test containers.

    By default, the session scope is used for LocalStack test containers.
    """
    return pytest.fixture(
        _multi_s3_container_fixture, scope="session", name="multi_s3_container"
    )


multi_s3_container_fixture = get_multi_s3_container_fixture()


def _persistent_federated_s3_fixture(
    multi_s3_container: MultiS3ContainerFixture,
) -> Generator[FederatedS3Fixture, None, None]:
    """Fixture function that gets a persistent FederatedS3Fixture.

    The state of each S3 storage in the fixture is not cleaned up.
    """
    storages = {}
    for name, container in multi_s3_container.s3_containers.items():
        config = container.s3_config
        storage = S3ObjectStorage(config=config)
        storages[name] = S3Fixture(config=config, storage=storage)
    yield FederatedS3Fixture(storages)


async def _clean_federated_s3_fixture(
    multi_s3_container: MultiS3ContainerFixture,
) -> AsyncGenerator[FederatedS3Fixture, None]:
    """Fixture function that gets a clean FederatedS3Fixture instance.

    The state of each S3 storage is cleaned up before yielding the fixture.
    """
    for federated_s3_fixture in _persistent_federated_s3_fixture(multi_s3_container):
        for s3_fixture in federated_s3_fixture.nodes.values():
            await s3_fixture.delete_buckets()
        yield federated_s3_fixture


def get_federated_s3_fixture(
    scope: PytestScope = "function", name: str = "federated_s3"
):
    """Get a federated S3 storage fixture with desired scope.

    The state of the S3 storage is not cleaned up by the fixture.
    """
    return pytest_asyncio.fixture(_clean_federated_s3_fixture, scope=scope, name=name)


federated_s3_fixture = get_federated_s3_fixture()
