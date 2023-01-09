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
"""This is... UPLOAD!!!"""

import asyncio
import hashlib
import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

from ghga_connector.cli import upload
from ghga_event_schemas import pydantic_ as event_schemas
from ghga_service_chassis_lib.utils import big_temp_file
from hexkit.config import config_from_yaml
from hexkit.providers.akafka import KafkaConfig, KafkaEventPublisher
from hexkit.providers.s3 import S3Config

BASE_DIR = Path(__file__).parent.parent


@config_from_yaml(prefix="tb")
class Config(S3Config, KafkaConfig):
    """
    Custom Config class for the test app.
    Defaults set for not running inside devcontainer.
    """

    file_metadata_event_topic: str
    file_metadata_event_type: str
    inbox_bucket: str
    submitter_pubkey: str


CONFIG = Config()


async def run_upload():
    """main"""
    file_id = os.urandom(16).hex()
    file_size = 20 * 1024**2
    file_data, file_size, checksum = generate_file(file_size=file_size)
    await populate_metadata(
        file_id=file_id, decrypted_size=file_size, decrypted_sha256=checksum
    )
    # need path for connector
    with NamedTemporaryFile() as tmp_file:
        tmp_file.write(file_data)
        tmp_file.seek(0)
        upload_file(file_id=file_id, file_path=tmp_file.name)


def generate_file(file_size: int):
    """Generate encrypted test file"""

    with big_temp_file(size=file_size) as random_data:
        random_data.seek(0)
        data = random_data.read()
        size = len(data)
        checksum = hashlib.sha256(data).hexdigest()
        return data, size, checksum


async def populate_metadata(file_id: str, decrypted_size: int, decrypted_sha256: str):
    """Populate metadedata submission schema and send event for UCS"""
    metadata_files = [
        event_schemas.MetadataSubmissionFiles(
            file_id=file_id,
            file_name="blue_milk.tar.gz",
            decrypted_size=decrypted_size,
            decrypted_sha256=decrypted_sha256,
        ),
    ]
    metadata_upserted = event_schemas.MetadataSubmissionUpserted(
        associated_files=metadata_files
    )

    async with KafkaEventPublisher.construct(config=CONFIG) as publisher:
        type_ = CONFIG.file_metadata_event_type
        key = file_id
        topic = CONFIG.file_metadata_event_topic
        await publisher.publish(
            payload=metadata_upserted.dict(),
            type_=type_,
            key=key,
            topic=topic,
        )
        time.sleep(10)


def upload_file(file_id: str, file_path: str):
    """Run file upload using the ghga-connector"""
    upload(
        file_id=file_id,
        file_path=file_path,
        pubkey_path=BASE_DIR / "example_data" / "key.pub",
    )


if __name__ == "__main__":
    asyncio.run(run_upload())
