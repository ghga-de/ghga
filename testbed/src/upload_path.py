# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This is... UPLOAD!!!"""

import asyncio
import os
import time
from tempfile import NamedTemporaryFile

from ghga_connector.cli import upload
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.providers.akafka import KafkaEventPublisher
from hexkit.providers.s3 import S3ObjectStorage

from src.commons import CONFIG, DATA_DIR, FILE_SIZE
from src.generate_data import generate_file


async def delegate_paths():
    """
    Generate and upload data for happy and unhappy paths
    Return file IDs for later checks
    """
    unencrypted_data, encrypted_data, checksum = generate_file()
    print("Uploading unencrypted file (unhappy path)")
    unencrypted_id = await populate_data(data=unencrypted_data, checksum=checksum)
    print("Uploading encrypted file (happy path)")
    encrypted_id = await populate_data(data=encrypted_data, checksum=checksum)
    return unencrypted_id, encrypted_id, unencrypted_data, checksum


async def populate_data(data: bytes, checksum: str):
    """Populate events, storage and check initial state"""
    file_id = os.urandom(16).hex()
    await populate_metadata_and_upload(
        file_id=file_id,
        file_name=file_id,
        data=data,
        size=FILE_SIZE,
        checksum=checksum,
    )
    await check_objectstorage(file_id=file_id)
    return file_id


async def populate_metadata_and_upload(
    file_id: str, file_name: str, data: bytes, size: int, checksum: str
):
    """Generate and send metadata event, afterwards upload data to object storage"""
    await populate_metadata(
        file_id=file_id,
        file_name=file_name,
        decrypted_size=size,
        decrypted_sha256=checksum,
    )
    # wait for possible delays in event delivery
    time.sleep(15)
    with NamedTemporaryFile() as tmp_file:
        tmp_file.write(data)
        tmp_file.flush()
        tmp_file.seek(0)
        upload(
            file_id=file_id,
            file_path=tmp_file.name,
            pubkey_path=DATA_DIR / "key.pub",
        )


async def populate_metadata(
    file_id: str, file_name: str, decrypted_size: int, decrypted_sha256: str
):
    """Populate metadedata submission schema and send event for UCS"""
    metadata_files = [
        event_schemas.MetadataSubmissionFiles(
            file_id=file_id,
            file_name=file_name,
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


async def check_objectstorage(file_id: str):
    """Check if object storage is populated"""
    storage = S3ObjectStorage(config=CONFIG)
    object_exists = await storage.does_object_exist(
        bucket_id=CONFIG.inbox_bucket, object_id=file_id
    )
    if not object_exists:
        raise ValueError("Object missing in inbox")


if __name__ == "__main__":
    asyncio.run(delegate_paths())
