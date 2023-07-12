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

from typing import Generator, Optional

from hexkit.providers.s3.provider import S3ObjectStorage
from hexkit.providers.s3.testutils import S3Fixture as BaseS3Fixture
from pytest import fixture

from fixtures.config import Config

__all__ = ["s3_fixture", "S3Fixture"]


class S3Fixture(BaseS3Fixture):
    """An augmented S3 fixture"""

    config: Config

    async def empty_buckets(self, bucket_id: Optional[str] = None):
        """Clean the test artifacts or files from given bucket"""
        if bucket_id is None:
            bucket_ids = [
                self.config.inbox_bucket,
                self.config.outbox_bucket,
                self.config.staging_bucket,
                self.config.permanent_bucket,
            ]
        else:
            bucket_ids = [bucket_id]

        for bucket in bucket_ids:
            # Get list of all objects in the bucket
            object_ids = await self.storage.list_all_object_ids(bucket_id=bucket)

            # Delete all objects
            for object_id in object_ids:
                await self.storage.delete_object(bucket_id=bucket, object_id=object_id)


@fixture(name="s3")
def s3_fixture(config: Config) -> Generator[S3Fixture, None, None]:
    """Pytest fixture for tests depending on the S3ObjectStorage."""

    storage = S3ObjectStorage(config=config)
    yield S3Fixture(config=config, storage=storage)
