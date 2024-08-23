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
"""Unit tests for the objects handler class"""

from contextlib import nullcontext
from unittest.mock import AsyncMock

import pytest
from ghga_service_commons.utils.multinode_storage import S3ObjectStoragesConfig
from hexkit.protocols.objstorage import ObjectStorageProtocol
from hexkit.providers.s3 import S3ObjectStorage

from sms.core.objects_handler import ObjectsHandler
from sms.ports.inbound.objects_handler import S3ObjectStoragesPort
from tests.fixtures.config import DEFAULT_TEST_CONFIG

pytestmark = pytest.mark.asyncio()

DEFAULT_ALIAS = "primary"


def check_id_validity(id_: str):
    """Mock version of the bucket/object ID validation functions.

    Just employs a simple length check.
    Returns True if it is valid, False if invalid.
    """
    return 3 <= len(id_) <= 63


def validate_bucket_id(bucket_id: str):
    """Mock version of the bucket ID validation function"""
    if not check_id_validity(bucket_id):
        raise ObjectStorageProtocol.BucketIdValidationError(bucket_id, reason=None)


def validate_object_id(object_id: str):
    """Mock version of the object ID validation function"""
    if not check_id_validity(object_id):
        raise ObjectStorageProtocol.ObjectIdValidationError(object_id, reason=None)


def get_storage_mock():
    """Initialize a mock object storage instance with a bucket and an object."""
    mock = AsyncMock(spec=S3ObjectStorage)
    mock.buckets = {"bucket": ["object1"]}

    async def does_bucket_exist(bucket_id: str):
        validate_bucket_id(bucket_id)
        return bucket_id in mock.buckets

    async def does_object_exist(bucket_id: str, object_id: str):
        validate_bucket_id(bucket_id)
        validate_object_id(object_id)
        return object_id in mock.buckets.get(bucket_id, [])

    async def delete_object(bucket_id: str, object_id: str):
        validate_bucket_id(bucket_id)
        validate_object_id(object_id)

        try:
            bucket = mock.buckets[bucket_id]
        except KeyError as err:
            raise ObjectStorageProtocol.BucketNotFoundError(bucket_id) from err

        object_index = bucket.index(object_id)
        del bucket[object_index]

    async def list_all_object_ids(bucket_id: str):
        validate_bucket_id(bucket_id)
        try:
            return mock.buckets[bucket_id]
        except KeyError as err:
            raise ObjectStorageProtocol.BucketNotFoundError(bucket_id) from err

    mock.does_object_exist.side_effect = does_object_exist
    mock.delete_object.side_effect = delete_object
    mock.list_all_object_ids.side_effect = list_all_object_ids
    mock.does_bucket_exist.side_effect = does_bucket_exist
    return mock


class DummyObjectStorages(S3ObjectStoragesPort):
    """Dummy S3ObjectStoragesPort implementation for testing.

    It will use the mock object storage instance for all operations.
    """

    def __init__(self, config: S3ObjectStoragesConfig):
        self._config = config
        self._storages = {alias: get_storage_mock() for alias in config.object_storages}

    def for_alias(self, alias: str = "primary"):
        """Get the object storage instance for a specific alias."""
        if alias not in self._storages:
            raise self.AliasNotConfiguredError(alias=alias)
        return self._storages[alias]


@pytest.mark.parametrize(
    "bucket_id, object_id, expected_result, error",
    [
        ("bucket", "object1", True, None),
        ("bucket", "non-existent-object", False, None),
        ("non-existent-bucket", "object1", False, ObjectsHandler.BucketNotFoundError),
        ("a", "object1", False, ObjectsHandler.InvalidBucketIdError),
        ("bucket", "a", False, ObjectsHandler.InvalidObjectIdError),
    ],
    ids=[
        "HappyPath",
        "NonExistentObject",
        "NonExistentBucket",
        "InvalidBucket",
        "InvalidObject",
    ],
)
async def test_does_object_exist(
    bucket_id: str,
    object_id: str,
    expected_result: bool,
    error: type[Exception] | None,
):
    """Test for seeing if object exists.

    Errors should only be raised for invalid bucket/object IDs. If the bucket does not
    exist, the result should be False.
    """
    storages = DummyObjectStorages(config=DEFAULT_TEST_CONFIG)
    objects_handler = ObjectsHandler(
        config=DEFAULT_TEST_CONFIG, object_storages=storages
    )

    with pytest.raises(error) if error else nullcontext():
        result = await objects_handler.does_object_exist(
            DEFAULT_ALIAS, bucket_id, object_id
        )
        assert result == expected_result


async def test_empty_bucket():
    """Test emptying a bucket.

    Test for happy path, invalid bucket ID, non-existent bucket, and empty bucket.
    """
    storages = DummyObjectStorages(config=DEFAULT_TEST_CONFIG)
    objects_handler = ObjectsHandler(
        config=DEFAULT_TEST_CONFIG, object_storages=storages
    )

    # happy path
    await objects_handler.empty_bucket(DEFAULT_ALIAS, "bucket")
    assert storages.for_alias(DEFAULT_ALIAS).buckets["bucket"] == []

    # nonexistent bucket
    with pytest.raises(objects_handler.BucketNotFoundError):
        await objects_handler.empty_bucket(DEFAULT_ALIAS, "non-existent-bucket")

    # invalid bucket name
    with pytest.raises(objects_handler.InvalidBucketIdError):
        await objects_handler.empty_bucket(DEFAULT_ALIAS, "a")

    # already empty bucket
    await objects_handler.empty_bucket(DEFAULT_ALIAS, "bucket")
    assert storages.for_alias(DEFAULT_ALIAS).buckets["bucket"] == []


async def test_list_objects():
    """Test listing objects in a bucket.

    Test for happy path, invalid bucket ID, non-existent bucket, and empty bucket.
    """
    storages = DummyObjectStorages(config=DEFAULT_TEST_CONFIG)
    objects_handler = ObjectsHandler(
        config=DEFAULT_TEST_CONFIG, object_storages=storages
    )

    # Happy path
    results = await objects_handler.list_objects(DEFAULT_ALIAS, "bucket")
    assert results == ["object1"]

    # Nonexistent bucket
    with pytest.raises(objects_handler.BucketNotFoundError):
        await objects_handler.list_objects(DEFAULT_ALIAS, "non-existent-bucket")

    # Invalid bucket name
    with pytest.raises(objects_handler.InvalidBucketIdError):
        await objects_handler.list_objects(DEFAULT_ALIAS, "a")

    # Empty bucket
    storages.for_alias(DEFAULT_ALIAS).buckets["bucket"] = []
    results = await objects_handler.list_objects(DEFAULT_ALIAS, "bucket")
    assert results == []


async def test_bad_alias():
    """Test that the right error is raised in each method when the alias is not configured."""
    storages = DummyObjectStorages(config=DEFAULT_TEST_CONFIG)
    objects_handler = ObjectsHandler(
        config=DEFAULT_TEST_CONFIG, object_storages=storages
    )

    with pytest.raises(storages.AliasNotConfiguredError):
        await objects_handler.does_object_exist(
            "non-existent-alias", "bucket", "object1"
        )

    with pytest.raises(storages.AliasNotConfiguredError):
        await objects_handler.empty_bucket("non-existent-alias", "bucket")

    with pytest.raises(storages.AliasNotConfiguredError):
        await objects_handler.list_objects("non-existent-alias", "bucket")


async def test_misc_error_handling():
    """Verify that unexpected errors are re-raised as OperationError."""
    storages = DummyObjectStorages(config=DEFAULT_TEST_CONFIG)
    storage = storages.for_alias(DEFAULT_ALIAS)
    storage.does_object_exist.side_effect = RuntimeError
    storage.delete_object.side_effect = RuntimeError
    storage.list_all_object_ids.side_effect = RuntimeError
    objects_handler = ObjectsHandler(
        config=DEFAULT_TEST_CONFIG, object_storages=storages
    )

    # Error during does_object_exist
    storage.does_object_exist.side_effect = Exception
    with pytest.raises(objects_handler.OperationError):
        await objects_handler.does_object_exist(DEFAULT_ALIAS, "bucket", "object1")

    # Error during delete_object
    storage.delete_object.side_effect = Exception
    with pytest.raises(objects_handler.OperationError):
        await objects_handler.empty_bucket(DEFAULT_ALIAS, "bucket")

    # Error during list_objects
    storage.list_all_object_ids.side_effect = Exception
    with pytest.raises(objects_handler.OperationError):
        await objects_handler.list_objects(DEFAULT_ALIAS, "bucket")
