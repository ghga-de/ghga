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
from typing import List

from ghga_service_chassis_lib.object_storage_dao_testing import ObjectFixture
from ghga_service_chassis_lib.s3_testing import (
    S3Fixture,
    s3_fixture_factory,
    upload_file,
)
from ghga_service_chassis_lib.utils import big_temp_file

from . import state

existing_buckets: List[str] = ["inbox", "outbox"]
existing_objects: List[ObjectFixture] = []

for file in state.FILES.values():
    if file.populate_storage:
        for storage_object in file.storage_objects:
            if storage_object.bucket_id not in existing_buckets:
                existing_buckets.append(storage_object.bucket_id)
            existing_objects.append(storage_object)

s3_fixture = s3_fixture_factory(
    existing_buckets=existing_buckets,
    existing_objects=existing_objects,
)


@dataclass
class BigObjectS3Fixture(S3Fixture):
    """Extends the S3Fixture to include information on a big file stored on storage."""

    big_object: ObjectFixture


def get_big_s3_object(
    s3_fixture: S3Fixture, object_size: int = 20 * 1024 * 1024
) -> ObjectFixture:
    """
    Extends the s3_fixture to also include a big file with the specified `file_size` on
    the provided s3 storage.
    """

    with big_temp_file(object_size) as big_file:

        object_fixture = ObjectFixture(
            file_path=big_file.name,
            bucket_id=s3_fixture.existing_buckets[0],
            object_id="big-downloadable",
        )

        # upload file to s3
        assert not s3_fixture.storage.does_object_exist(
            bucket_id=object_fixture.bucket_id, object_id=object_fixture.object_id
        )
        presigned_url = s3_fixture.storage.get_object_upload_url(
            bucket_id=object_fixture.bucket_id,
            object_id=object_fixture.object_id,
        )
        upload_file(
            presigned_url=presigned_url,
            file_path=big_file.name,
            file_md5=object_fixture.md5,
        )

    return object_fixture
