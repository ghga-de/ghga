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

"""Fixture for testing code that uses the S3ObjectStorage provider."""

import asyncio
from typing import Generator

from hexkit.providers.s3.provider import S3ObjectStorage
from hexkit.providers.s3.testutils import S3Fixture
from pytest import fixture

from fixtures.config import Config

__all__ = ["s3_fixture", "S3Fixture"]


async def empty_storage_bucket(storage: S3ObjectStorage, bucket_id: str):
    """Clean the test artifacts or files from given bucket"""

    # Get list of all object in bucket
    object_ids = await storage.list_all_object_ids(bucket_id=bucket_id)

    # Delete all objects
    for object_id in object_ids:
        await storage.delete_object(bucket_id=bucket_id, object_id=object_id)


@fixture(name="s3")
def s3_fixture(config: Config) -> Generator[S3Fixture, None, None]:
    """Pytest fixture for tests depending on the S3ObjectStorage."""

    storage = S3ObjectStorage(config=config)
    yield S3Fixture(config=config, storage=storage)

    # Empty all storage buckets
    for bucket_id in [
        config.inbox_bucket,
        config.outbox_bucket,
        config.staging_bucket,
        config.permanent_bucket,
    ]:
        asyncio.run(empty_storage_bucket(storage, bucket_id))
