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

"""Integration tests for the MongoDbBoxStatsAggregator"""

from uuid import UUID, uuid4

import pytest
from hexkit.correlation import set_correlation_id

from tests_ucs.fixtures import utils
from tests_ucs.fixtures.joint import JointFixture
from ucs.constants import COUNTED_UPLOAD_STATES
from ucs.core.controller import UploadController

pytestmark = pytest.mark.asyncio()

NOT_COUNTED_UPLOAD_STATES = ("init", "failed", "cancelled")


async def test_box_stats_aggregation(joint_fixture: JointFixture):
    """Test MongoDbBoxStatsAggregator.compute_box_stats against a real MongoDB instance.

    The FileUpload documents are written through the DAO so that the docs in the DB
    more reliably have the correct structure, e.g. __metadata__, field encoding, etc.
    """
    controller = joint_fixture.upload_controller
    assert isinstance(controller, UploadController)
    box_stats_aggregator = controller._box_stats_aggregator
    file_upload_dao = controller._file_upload_dao

    box_id = uuid4()
    other_box_id = uuid4()

    # Try calculating stats box without any FileUploads
    assert await box_stats_aggregator.compute_box_stats(box_id=box_id) == (0, 0)

    # Insert one FileUpload per state, each with a distinct decrypted_size
    counted_sizes_by_file_id: dict[UUID, int] = {}
    not_counted_size_total = 0
    async with set_correlation_id(uuid4()):
        for index, state in enumerate(
            COUNTED_UPLOAD_STATES + NOT_COUNTED_UPLOAD_STATES
        ):
            file_upload = utils.make_file_upload(state=state)
            file_upload.box_id = box_id
            file_upload.alias = f"file_{state}"
            file_upload.decrypted_size = 100 * (index + 1)
            await file_upload_dao.insert(file_upload)
            if state in COUNTED_UPLOAD_STATES:
                counted_sizes_by_file_id[file_upload.id] = file_upload.decrypted_size
            else:
                not_counted_size_total += file_upload.decrypted_size

        # Also insert a 'counted' FileUpload into a different box
        other_box_file_upload = utils.make_file_upload(state="inbox")
        other_box_file_upload.box_id = other_box_id
        await file_upload_dao.insert(other_box_file_upload)

    # Only the counted states of the requested box may contribute to the stats
    assert not_counted_size_total > 0
    file_count, total_size = await box_stats_aggregator.compute_box_stats(box_id=box_id)
    assert file_count == len(COUNTED_UPLOAD_STATES)
    assert total_size == sum(counted_sizes_by_file_id.values())

    # Make sure calc only considers files owned by the given box
    file_count, total_size = await box_stats_aggregator.compute_box_stats(
        box_id=other_box_id
    )
    assert file_count == 1
    assert total_size == other_box_file_upload.decrypted_size

    # Make sure 'deleted' outbox docs are not counted somehow
    deleted_file_id, _ = counted_sizes_by_file_id.popitem()
    async with set_correlation_id(uuid4()):
        await file_upload_dao.delete(deleted_file_id)
    file_count, total_size = await box_stats_aggregator.compute_box_stats(box_id=box_id)
    assert file_count == len(COUNTED_UPLOAD_STATES) - 1
    assert total_size == sum(counted_sizes_by_file_id.values())
