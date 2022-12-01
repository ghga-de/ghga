# Copyright 2022 Universität Tübingen, DKFZ and EMBL
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

import hashlib
import math
from dataclasses import dataclass

import pytest_asyncio  # type: ignore
import requests  # type: ignore
from ghga_service_chassis_lib.utils import big_temp_file  # type: ignore
from hexkit.providers.s3 import S3ObjectStorage  # type: ignore

from tests.fixtures.config import CONFIG

PART_SIZE = 8 * 1024**2


@dataclass
class CheckablePayloadFields:
    """Fields from recorded event that hold values that can and should be checked"""

    file_id: str
    part_size: int
    content_checksum: str


@dataclass
class PopulatedS3Fixture:
    """Holds S3 storage initialized with test object present and relevant metadata"""

    storage: S3ObjectStorage
    file_size: int
    checksum: str


@pytest_asyncio.fixture
async def populated_s3_fixture() -> S3ObjectStorage:
    """Clean bucket and object"""

    file_size = 20 * 1024**2
    num_parts = math.ceil(file_size / PART_SIZE)
    storage = S3ObjectStorage(config=CONFIG)

    if not await storage.does_bucket_exist(bucket_id=CONFIG.inbox_bucket):
        await storage.create_bucket(bucket_id=CONFIG.inbox_bucket)
    if await storage.does_object_exist(
        bucket_id=CONFIG.inbox_bucket, object_id=CONFIG.object_id
    ):
        await storage.delete_object(
            bucket_id=CONFIG.inbox_bucket, object_id=CONFIG.object_id
        )

    with big_temp_file(size=file_size) as random_data:

        checksum = hashlib.sha256(random_data.read()).hexdigest()
        # rewind file
        random_data.seek(0)

        upload_id = await storage.init_multipart_upload(
            bucket_id=CONFIG.inbox_bucket, object_id=CONFIG.object_id
        )
        try:
            for part_number in range(1, num_parts + 1):

                part = random_data.read(PART_SIZE)
                upload_url = await storage.get_part_upload_url(
                    upload_id=upload_id,
                    bucket_id=CONFIG.inbox_bucket,
                    object_id=CONFIG.object_id,
                    part_number=part_number,
                )
                response = requests.put(url=upload_url, data=part, timeout=2)
                assert response.status_code == 200

            await storage.complete_multipart_upload(
                upload_id=upload_id,
                bucket_id=CONFIG.inbox_bucket,
                object_id=CONFIG.object_id,
            )

        except (Exception, KeyboardInterrupt):
            await storage.abort_multipart_upload(
                upload_id=upload_id,
                bucket_id=CONFIG.inbox_bucket,
                object_id=CONFIG.object_id,
            )

    yield PopulatedS3Fixture(storage=storage, file_size=file_size, checksum=checksum)
