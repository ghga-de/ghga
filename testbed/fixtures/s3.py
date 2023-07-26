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

from typing import Generator, Union

from hexkit.providers.s3.provider import S3ObjectStorage
from hexkit.providers.s3.testutils import S3Fixture as BaseS3Fixture
from pytest import fixture

from fixtures.config import Config

__all__ = ["s3_fixture", "S3Fixture"]


class S3Fixture(BaseS3Fixture):
    """An augmented S3 fixture"""

    config: Config

    @property
    def all_buckets(self) -> list[str]:
        config = self.config
        return [
            config.inbox_bucket,
            config.outbox_bucket,
            config.staging_bucket,
            config.permanent_bucket,
        ]

    async def empty_given_buckets(self, buckets: Union[str, list[str]]):
        """Empty only the specified bucket(s)."""
        if isinstance(buckets, str):
            buckets = [buckets]
        bucket_set = set(buckets)
        exclude = [bucket for bucket in self.all_buckets if bucket not in bucket_set]
        await self.empty_buckets(buckets_to_exclude=exclude)


@fixture(name="s3", scope="session")
def s3_fixture(config: Config) -> Generator[S3Fixture, None, None]:
    """Pytest fixture for tests depending on the S3ObjectStorage."""

    storage = S3ObjectStorage(config=config)
    yield S3Fixture(config=config, storage=storage)
