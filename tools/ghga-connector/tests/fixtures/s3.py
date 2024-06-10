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

"""Fixtures for testing the storage DAO"""

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path

import pytest
import pytest_asyncio
from ghga_service_commons.utils.temp_files import big_temp_file
from hexkit.providers.s3 import S3Config, S3ObjectStorage
from hexkit.providers.s3.testutils import (
    TEST_FILE_PATHS,
    FileObject,
    config_from_localstack_container,
    upload_file,
)
from pydantic import PrivateAttr
from testcontainers.localstack import LocalStackContainer

from . import state

DEFAULT_EXISTING_BUCKETS = [
    "myexistingtestbucket100",
    "myexistingtestbucket200",
]
DEFAULT_NON_EXISTING_BUCKETS = [
    "mynonexistingtestobject100",
    "mynonexistingtestobject200",
]

DEFAULT_EXISTING_OBJECTS = [
    FileObject(
        file_path=file_path,
        bucket_id=f"myexistingtestbucket{idx}",
        object_id=f"myexistingtestobject{idx}",
    )
    for idx, file_path in enumerate(TEST_FILE_PATHS[0:2])
]

DEFAULT_NON_EXISTING_OBJECTS = [
    FileObject(
        file_path=file_path,
        bucket_id=f"mynonexistingtestbucket{idx}",
        object_id=f"mynonexistingtestobject{idx}",
    )
    for idx, file_path in enumerate(TEST_FILE_PATHS[2:4])
]

existing_buckets: list[str] = ["inbox", "outbox"]
existing_objects: list[FileObject] = []

for file in state.FILES.values():
    if file.populate_storage:
        for storage_object in file.storage_objects:
            if storage_object.bucket_id not in existing_buckets:
                existing_buckets.append(storage_object.bucket_id)
            existing_objects.append(storage_object)

EXISTING_BUCKETS_ = (
    DEFAULT_EXISTING_BUCKETS if existing_buckets is None else existing_buckets
)
NON_EXISTING_BUCKETS_ = DEFAULT_NON_EXISTING_BUCKETS
EXISTING_OBJECTS_ = (
    DEFAULT_EXISTING_OBJECTS if existing_objects is None else existing_objects
)
NON_EXISTING_OBJECTS_ = DEFAULT_NON_EXISTING_OBJECTS


class CachedFileObject(FileObject):
    """A subclass of FileObject that adds caching to the `content` property."""

    _cached_content: bytes = PrivateAttr(default=b"")
    _is_cached: bool = PrivateAttr(default=False)

    @property
    def content(self) -> bytes:
        """
        Overrides the computed 'content' property of FileObject to cache the content,
        useful if the file is temporary and may be removed.
        """
        if not self._is_cached:
            self._cached_content = super().content
            self._is_cached = True
        return self._cached_content


@dataclass
class S3Fixture:
    """Info yielded by the `s3_fixture` function"""

    config: S3Config
    storage: S3ObjectStorage
    existing_buckets: list[str]
    non_existing_buckets: list[str]
    existing_objects: list[FileObject]
    non_existing_objects: list[FileObject]

    async def reset_state(self):
        """Reset to populated_fixture state"""
        for bucket in self.existing_buckets:
            await self.storage.delete_bucket(bucket_id=bucket, delete_content=True)
        self.existing_buckets = EXISTING_BUCKETS_
        self.non_existing_buckets = NON_EXISTING_BUCKETS_
        self.existing_objects = EXISTING_OBJECTS_
        self.non_existing_objects = NON_EXISTING_OBJECTS_

        await populate_storage(
            storage=self.storage,
            bucket_fixtures=EXISTING_BUCKETS_,
            object_fixtures=EXISTING_OBJECTS_,
        )


@pytest.fixture(scope="function", autouse=True)
def reset_state(s3_fixture: S3Fixture):
    """Reset S3 state between tests"""
    yield
    loop = asyncio.get_event_loop()
    loop.run_until_complete(s3_fixture.reset_state())


async def populate_storage(
    storage: S3ObjectStorage,
    bucket_fixtures: list[str],
    object_fixtures: list[FileObject],
):
    """Populate Storage with object and bucket fixtures"""
    for bucket_fixture in bucket_fixtures:
        await storage.create_bucket(bucket_fixture)

    for object_fixture in object_fixtures:
        if not await storage.does_bucket_exist(object_fixture.bucket_id):
            await storage.create_bucket(object_fixture.bucket_id)

        presigned_url = await storage.get_object_upload_url(
            bucket_id=object_fixture.bucket_id, object_id=object_fixture.object_id
        )

        upload_file(
            presigned_url=presigned_url,
            file_path=object_fixture.file_path,
            file_md5=object_fixture.md5,
        )


@pytest_asyncio.fixture(scope="session")
async def s3_fixture() -> AsyncGenerator[S3Fixture, None]:
    """Pytest fixture for tests depending on the ObjectStorageS3 DAO."""
    with LocalStackContainer(image="localstack/localstack:0.14.5").with_services(
        "s3"
    ) as localstack:
        config = config_from_localstack_container(localstack)
        storage = S3ObjectStorage(config=config)
        await populate_storage(
            storage=storage,
            bucket_fixtures=EXISTING_BUCKETS_,
            object_fixtures=EXISTING_OBJECTS_,
        )

        assert not set(EXISTING_BUCKETS_) & set(  # nosec
            NON_EXISTING_BUCKETS_
        ), "The existing and non existing bucket lists may not overlap"

        yield S3Fixture(
            config=config,
            storage=storage,
            existing_buckets=EXISTING_BUCKETS_,
            non_existing_buckets=NON_EXISTING_BUCKETS_,
            existing_objects=EXISTING_OBJECTS_,
            non_existing_objects=NON_EXISTING_OBJECTS_,
        )


@dataclass
class BigObjectS3Fixture(S3Fixture):
    """Extends the S3Fixture to include information on a big file stored on storage."""

    big_object: FileObject


async def get_big_s3_object(
    s3: S3Fixture, object_size: int = 20 * 1024 * 1024
) -> CachedFileObject:
    """
    Extends the s3_fixture to also include a big file with the specified `file_size` on
    the provided s3 storage.
    """
    with big_temp_file(object_size) as big_file:
        file_path = Path(big_file.name)
        object_fixture = CachedFileObject(
            file_path=file_path,
            bucket_id=s3.existing_buckets[0],
            object_id="big-downloadable",
        )

        # upload file to s3
        assert not await s3.storage.does_object_exist(
            bucket_id=object_fixture.bucket_id, object_id=object_fixture.object_id
        )
        presigned_url = await s3.storage.get_object_upload_url(
            bucket_id=object_fixture.bucket_id,
            object_id=object_fixture.object_id,
        )
        upload_file(
            presigned_url=presigned_url,
            file_path=file_path,
            file_md5=object_fixture.md5,
        )

    return object_fixture
