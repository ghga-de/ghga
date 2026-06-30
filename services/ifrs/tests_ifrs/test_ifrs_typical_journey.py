# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Tests typical user journeys"""

from uuid import uuid4

import pytest
import requests
from hexkit.protocols.dao import ResourceNotFoundError
from hexkit.providers.akafka.testutils import ExpectedEvent
from hexkit.providers.s3.testutils import (
    FileObject,
    tmp_file,  # noqa: F401
)

from tests_ifrs.fixtures.example_data import EXAMPLE_ARCHIVABLE_FILE
from tests_ifrs.fixtures.joint import JointFixture
from tests_ifrs.fixtures.utils import (
    DOWNLOAD_BUCKET,
    INTERROGATION_BUCKET,
    PERMANENT_BUCKET,
)

pytestmark = pytest.mark.asyncio


async def test_happy_journey(
    joint_fixture: JointFixture,
    tmp_file: FileObject,  # noqa: F811
):
    """Simulates a typical, successful journey for upload, download, and deletion"""
    storage_alias = joint_fixture.storage_aliases.node0
    storage = joint_fixture.federated_s3.storages[storage_alias]

    permanent_bucket_id = joint_fixture.config.object_storages[storage_alias].bucket
    # place example content in the interrogation bucket:
    file_object = tmp_file.model_copy(
        update={
            "bucket_id": INTERROGATION_BUCKET,
            "object_id": str(EXAMPLE_ARCHIVABLE_FILE.object_id),
        }
    )

    # Populate test object, get the object size, and create the ArchivableFileUpload
    await storage.populate_file_objects(file_objects=[file_object])
    archivable_file = EXAMPLE_ARCHIVABLE_FILE.model_copy(
        update={
            "storage_alias": storage_alias,
            "encrypted_size": len(tmp_file.content),
        },
        deep=True,
    )
    assert archivable_file.bucket_id == INTERROGATION_BUCKET  # just double checking

    # register new file from the interrogation bucket and make sure event is published
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.file_internally_registered_topic,
    ) as recorder:
        await joint_fixture.file_registry.register_file(file=archivable_file)

    stored_metadata = await joint_fixture.file_metadata_dao.get_by_id(
        archivable_file.id
    )
    assert len(recorder.recorded_events) == 1
    event = recorder.recorded_events[0]
    assert event.type_ == joint_fixture.config.file_internally_registered_type
    assert event.key == str(stored_metadata.id)
    assert stored_metadata.bucket_id != archivable_file.bucket_id
    assert stored_metadata.bucket_id == permanent_bucket_id == PERMANENT_BUCKET
    assert stored_metadata.object_id != archivable_file.object_id
    stored_dumped = stored_metadata.model_dump(mode="json")
    event_payload = dict(event.payload)
    assert event_payload.pop("file_id") == stored_dumped.pop("id")

    # check that the file content is now in both the interrogation and permanent buckets
    assert await storage.storage.does_object_exist(
        bucket_id=archivable_file.bucket_id,
        object_id=str(archivable_file.object_id),
    )
    assert await storage.storage.does_object_exist(
        bucket_id=permanent_bucket_id,
        object_id=str(stored_metadata.object_id),
    )

    # request a stage to the download bucket and check for the "file staged" event:
    download_object_id = uuid4()
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.file_staged_topic,
    ) as recorder:
        await joint_fixture.file_registry.stage_registered_file(
            file_id=archivable_file.id,
            decrypted_sha256=archivable_file.decrypted_sha256,
            download_object_id=download_object_id,
            download_bucket_id=DOWNLOAD_BUCKET,
        )
    events = recorder.recorded_events
    assert len(events) == 1
    assert events[0].type_ == joint_fixture.config.file_staged_type
    assert events[0].key == str(archivable_file.id)
    assert events[0].payload == {
        "file_id": events[0].key,
        "storage_alias": storage_alias,
        "target_bucket_id": DOWNLOAD_BUCKET,
        "target_object_id": str(download_object_id),
        "decrypted_sha256": archivable_file.decrypted_sha256,
    }

    # check that the file content is now in all three storage entities:
    assert await storage.storage.does_object_exist(
        bucket_id=INTERROGATION_BUCKET,
        object_id=str(archivable_file.object_id),
    )
    assert await storage.storage.does_object_exist(
        bucket_id=permanent_bucket_id,
        object_id=str(stored_metadata.object_id),
    )
    assert await storage.storage.does_object_exist(
        bucket_id=DOWNLOAD_BUCKET,
        object_id=str(download_object_id),
    )

    # check that the file content in the download bucket is identical to the content in
    # the interrogation bucket.
    download_url = await storage.storage.get_object_download_url(
        bucket_id=DOWNLOAD_BUCKET,
        object_id=str(download_object_id),
    )
    response = requests.get(download_url, timeout=60)
    response.raise_for_status()
    assert response.content == file_object.content

    # Request file deletion:
    async with joint_fixture.kafka.expect_events(
        events=[
            ExpectedEvent(
                payload={"file_id": archivable_file.id},
                type_=joint_fixture.config.file_deleted_type,
            )
        ],
        in_topic=joint_fixture.config.file_deleted_topic,
    ):
        await joint_fixture.file_registry.delete_file(file_id=archivable_file.id)

    # Verify that the file is no longer in the permanent bucket
    assert not await storage.storage.does_object_exist(
        bucket_id=permanent_bucket_id,
        object_id=str(stored_metadata.object_id),
    )

    # Verify that the metadata has also been removed
    with pytest.raises(ResourceNotFoundError):
        _ = await joint_fixture.file_metadata_dao.get_by_id(archivable_file.id)
