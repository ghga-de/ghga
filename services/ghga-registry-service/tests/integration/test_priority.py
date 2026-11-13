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

"""Test that the upload box priority list is published through the outbox."""

from uuid import uuid4

import pytest

from ghga_service_commons.http.mock_api import respond
from rs.constants import BOX_PRIORITY_EVENT_KEY, UPLOAD_BOX_PRIORITY_COLLECTION
from rs.core.models import UploadBoxPriority
from tests.fixtures.joint import JointFixture
from tests.fixtures.utils import TEST_MAX_SIZE

pytestmark = pytest.mark.asyncio


async def test_box_changes_publish_priority(joint_fixture: JointFixture):
    """Test that creating boxes publishes the list each time, and that a repair that
    changes nothing publishes nothing.
    """
    rdub_manager = joint_fixture.registry.rdub_manager
    priority_manager = joint_fixture.registry.priority_manager
    topic = joint_fixture.config.upload_box_priority_topic
    data_steward_id = uuid4()

    box_ids = []
    file_upload_box_ids = []
    async with joint_fixture.kafka.record_events(in_topic=topic) as recorder:
        for i in range(2):
            file_upload_box_ids.append(uuid4())
            joint_fixture.file_box_api.on_create_file_upload_box = respond(
                201, json=str(file_upload_box_ids[-1])
            )
            box_ids.append(
                await rdub_manager.create_research_data_upload_box(
                    title=f"Box {i}",
                    description="A box for the priority test",
                    storage_alias="test-storage",
                    data_steward_id=data_steward_id,
                    max_size=TEST_MAX_SIZE,
                )
            )

    assert len(recorder.recorded_events) == 2
    event = recorder.recorded_events[-1]
    assert event.type_ == "upserted"
    assert event.key == BOX_PRIORITY_EVENT_KEY
    priority = UploadBoxPriority.model_validate(event.payload)
    assert priority.version == 2
    assert priority.changed_by == data_steward_id
    assert [entry.research_data_upload_box_id for entry in priority.entries] == box_ids
    assert [
        entry.file_upload_box_id for entry in priority.entries
    ] == file_upload_box_ids

    async with joint_fixture.kafka.record_events(in_topic=topic) as recorder:
        await priority_manager.repair()

    assert recorder.recorded_events == []


async def test_repair_publishes_priority(joint_fixture: JointFixture):
    """Test that a repair that changes the list publishes it on behalf of the system,
    as when RS starts with boxes that existed before the list.
    """
    joint_fixture.file_box_api.on_create_file_upload_box = respond(
        201, json=str(uuid4())
    )
    box_id = await joint_fixture.registry.rdub_manager.create_research_data_upload_box(
        title="Box",
        description="A box for the repair test",
        storage_alias="test-storage",
        data_steward_id=uuid4(),
        max_size=TEST_MAX_SIZE,
    )
    joint_fixture.mongodb.empty_collections(collections=UPLOAD_BOX_PRIORITY_COLLECTION)

    topic = joint_fixture.config.upload_box_priority_topic
    async with joint_fixture.kafka.record_events(in_topic=topic) as recorder:
        await joint_fixture.registry.priority_manager.repair()

    assert len(recorder.recorded_events) == 1
    priority = UploadBoxPriority.model_validate(recorder.recorded_events[0].payload)
    assert priority.version == 1
    assert priority.changed_by is None
    assert [entry.research_data_upload_box_id for entry in priority.entries] == [box_id]
