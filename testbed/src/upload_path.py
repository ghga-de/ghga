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

"""Functionality for file uploading"""

import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

from ghga_connector.cli import upload
from ghga_event_schemas import pydantic_ as event_schemas

from src.generate_data import generate_file
from tests.fixtures import JointFixture


async def delegate_paths(fixtures: JointFixture):
    """
    Generate and upload data for happy and unhappy paths
    Return file IDs for later checks
    """
    config = fixtures.config
    unencrypted_data, encrypted_data, checksum = generate_file(config=config)
    print("Uploading unencrypted file (unhappy path)")
    unencrypted_id = await populate_data(
        data=unencrypted_data, checksum=checksum, fixtures=fixtures
    )
    print("Uploading encrypted file (happy path)")
    encrypted_id = await populate_data(
        data=encrypted_data, checksum=checksum, fixtures=fixtures
    )
    return unencrypted_id, encrypted_id, unencrypted_data, checksum


async def populate_data(data: bytes, checksum: str, fixtures: JointFixture):
    """Populate events, storage and check initial state"""
    file_id = os.urandom(16).hex()
    await populate_metadata_and_upload(
        file_id=file_id,
        file_name=file_id,
        data=data,
        size=fixtures.config.file_size,
        checksum=checksum,
        fixtures=fixtures,
    )
    await check_objectstorage(file_id=file_id, fixtures=fixtures)
    return file_id


# pylint: disable=too-many-arguments
async def populate_metadata_and_upload(
    file_id: str,
    file_name: str,
    data: bytes,
    size: int,
    checksum: str,
    fixtures: JointFixture,
):
    """Generate and send metadata event, afterwards upload data to object storage"""
    await populate_metadata(
        file_id=file_id,
        file_name=file_name,
        decrypted_size=size,
        decrypted_sha256=checksum,
        fixtures=fixtures,
    )
    # wait for possible delays in event delivery
    time.sleep(15)
    with NamedTemporaryFile() as tmp_file:
        tmp_file.write(data)
        tmp_file.flush()
        tmp_file.seek(0)
        upload(
            file_id=file_id,
            file_path=Path(tmp_file.name),
            pubkey_path=fixtures.config.data_dir / "key.pub",
        )


async def populate_metadata(
    file_id: str,
    file_name: str,
    decrypted_size: int,
    decrypted_sha256: str,
    fixtures: JointFixture,
):
    """Populate metadata submission schema and send event for UCS"""
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

    config = fixtures.config
    type_ = config.file_metadata_event_type
    key = file_id
    topic = config.file_metadata_event_topic
    await fixtures.kafka.publisher.publish(
        payload=metadata_upserted.dict(),
        type_=type_,
        key=key,
        topic=topic,
    )


async def check_objectstorage(file_id: str, fixtures: JointFixture):
    """Check if object storage is populated"""
    object_exists = await fixtures.s3.storage.does_object_exist(
        bucket_id=fixtures.config.inbox_bucket, object_id=file_id
    )
    if not object_exists:
        raise ValueError("Object missing in inbox")
