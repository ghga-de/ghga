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

"""Fixtures for testing the storage DAO"""

from dataclasses import dataclass
from typing import AsyncGenerator, List

import pytest_asyncio
from ghga_service_commons.utils.temp_files import big_temp_file
from hexkit.providers.s3 import S3Config, S3ObjectStorage
from hexkit.providers.s3.testutils import (
    TEST_FILE_PATHS,
    FileObject,
    config_from_localstack_container,
    upload_file,
)
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

existing_buckets: List[str] = ["inbox", "outbox"]
existing_objects: List[FileObject] = []

for file in state.FILES.values():
    if file.populate_storage:
        for storage_object in file.storage_objects:
            if storage_object.bucket_id not in existing_buckets:
                existing_buckets.append(storage_object.bucket_id)
            existing_objects.append(storage_object)

existing_buckets_ = (
    DEFAULT_EXISTING_BUCKETS if existing_buckets is None else existing_buckets
)
non_existing_buckets_ = DEFAULT_NON_EXISTING_BUCKETS
existing_objects_ = (
    DEFAULT_EXISTING_OBJECTS if existing_objects is None else existing_objects
)
non_existing_objects_ = DEFAULT_NON_EXISTING_OBJECTS


@dataclass
class S3Fixture:
    """Info yielded by the `s3_fixture` function"""

    config: S3Config
    storage: S3ObjectStorage
    existing_buckets: List[str]
    non_existing_buckets: List[str]
    existing_objects: List[FileObject]
    non_existing_objects: List[FileObject]


async def populate_storage(
    storage: S3ObjectStorage,
    bucket_fixtures: List[str],
    object_fixtures: List[FileObject],
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


@pytest_asyncio.fixture
async def s3_fixture() -> AsyncGenerator[S3Fixture, None]:
    """Pytest fixture for tests depending on the ObjectStorageS3 DAO."""
    with LocalStackContainer(image="localstack/localstack:0.14.2").with_services(
        "s3"
    ) as localstack:
        config = config_from_localstack_container(localstack)
        storage = S3ObjectStorage(config=config)
        await populate_storage(
            storage=storage,
            bucket_fixtures=existing_buckets_,
            object_fixtures=existing_objects_,
        )

        assert not set(existing_buckets_) & set(  # nosec
            non_existing_buckets_
        ), "The existing and non existing bucket lists may not overlap"

        yield S3Fixture(
            config=config,
            storage=storage,
            existing_buckets=existing_buckets_,
            non_existing_buckets=non_existing_buckets_,
            existing_objects=existing_objects_,
            non_existing_objects=non_existing_objects_,
        )


@dataclass
class BigObjectS3Fixture(S3Fixture):
    """Extends the S3Fixture to include information on a big file stored on storage."""

    big_object: FileObject


async def get_big_s3_object(
    s3: S3Fixture, object_size: int = 20 * 1024 * 1024
) -> FileObject:
    """
    Extends the s3_fixture to also include a big file with the specified `file_size` on
    the provided s3 storage.
    """
    with big_temp_file(object_size) as big_file:
        object_fixture = FileObject(
            file_path=big_file.name,
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
            file_path=big_file.name,
            file_md5=object_fixture.md5,
        )

    return object_fixture
