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

"""Tests typical user journeys"""

from typing import cast

import pytest
import requests
from hexkit.providers.akafka.testutils import ExpectedEvent
from hexkit.providers.s3.testutils import (
    FileObject,
    file_fixture,  # noqa: F401
)

from tests.fixtures.example_data import EXAMPLE_METADATA, EXAMPLE_METADATA_BASE
from tests.fixtures.module_scope_fixtures import (  # noqa: F401
    JointFixture,
    joint_fixture,
    kafka_fixture,
    mongodb_fixture,
    reset_state,
    s3_fixture,
    second_s3_fixture,
)


@pytest.mark.asyncio(scope="session")
async def test_happy_journey(
    joint_fixture: JointFixture,  # noqa: F811
    file_fixture: FileObject,  # noqa: F811
):
    """Simulates a typical, successful journey for upload, download, and deletion"""
    for s3, strorage_alias in (
        (joint_fixture.s3, joint_fixture.endpoint_aliases.node1),
        (joint_fixture.second_s3, joint_fixture.endpoint_aliases.node2),
    ):
        bucket_id = joint_fixture.config.object_storages[strorage_alias].bucket
        # place example content in the staging:
        file_object = file_fixture.model_copy(
            update={
                "bucket_id": joint_fixture.staging_bucket,
                "object_id": EXAMPLE_METADATA.object_id,
            }
        )
        await s3.populate_file_objects(file_objects=[file_object])

        # register new file from the staging:
        # (And check if an event informing about the new registration has been published.)
        file_metadata_base = EXAMPLE_METADATA_BASE.model_copy(
            update={"storage_alias": strorage_alias}, deep=True
        )

        async with joint_fixture.kafka.record_events(
            in_topic=joint_fixture.config.file_registered_event_topic,
        ) as recorder:
            await joint_fixture.file_registry.register_file(
                file_without_object_id=file_metadata_base,
                staging_object_id=EXAMPLE_METADATA.object_id,
                staging_bucket_id=joint_fixture.staging_bucket,
            )

        assert len(recorder.recorded_events) == 1
        event = recorder.recorded_events[0]
        assert event.payload["object_id"] != ""
        assert event.type_ == joint_fixture.config.file_registered_event_type

        object_id = cast(str, event.payload["object_id"])

        # check that the file content is now in both the staging and the permanent storage:
        assert await s3.storage.does_object_exist(
            bucket_id=joint_fixture.staging_bucket,
            object_id=EXAMPLE_METADATA.object_id,
        )
        assert await s3.storage.does_object_exist(
            bucket_id=bucket_id,
            object_id=object_id,
        )

        # request a stage to the outbox:
        async with joint_fixture.kafka.expect_events(
            events=[
                ExpectedEvent(
                    payload={
                        "file_id": file_metadata_base.file_id,
                        "decrypted_sha256": file_metadata_base.decrypted_sha256,
                        "target_object_id": EXAMPLE_METADATA.object_id,
                        "target_bucket_id": joint_fixture.outbox_bucket,
                        "s3_endpoint_alias": strorage_alias,
                    },
                    type_=joint_fixture.config.file_staged_event_type,
                    key=file_metadata_base.file_id,
                )
            ],
            in_topic=joint_fixture.config.file_staged_event_topic,
        ):
            await joint_fixture.file_registry.stage_registered_file(
                file_id=file_metadata_base.file_id,
                decrypted_sha256=file_metadata_base.decrypted_sha256,
                outbox_object_id=EXAMPLE_METADATA.object_id,
                outbox_bucket_id=joint_fixture.outbox_bucket,
            )

        # check that the file content is now in all three storage entities:
        assert await s3.storage.does_object_exist(
            bucket_id=joint_fixture.staging_bucket,
            object_id=EXAMPLE_METADATA.object_id,
        )
        assert await s3.storage.does_object_exist(
            bucket_id=bucket_id,
            object_id=object_id,
        )
        assert await s3.storage.does_object_exist(
            bucket_id=joint_fixture.outbox_bucket, object_id=EXAMPLE_METADATA.object_id
        )

        # check that the file content in the outbox is identical to the content in the
        # staging:
        download_url = await s3.storage.get_object_download_url(
            bucket_id=joint_fixture.outbox_bucket, object_id=EXAMPLE_METADATA.object_id
        )
        response = requests.get(download_url, timeout=60)
        response.raise_for_status()
        assert response.content == file_object.content

        # Request file deletion:
        async with joint_fixture.kafka.expect_events(
            events=[
                ExpectedEvent(
                    payload={"file_id": file_metadata_base.file_id},
                    type_=joint_fixture.config.file_deleted_event_type,
                )
            ],
            in_topic=joint_fixture.config.file_deleted_event_topic,
        ):
            await joint_fixture.file_registry.delete_file(
                file_id=file_metadata_base.file_id,
            )

        assert not await s3.storage.does_object_exist(
            bucket_id=bucket_id,
            object_id=object_id,
        )

        await joint_fixture.reset_state()
