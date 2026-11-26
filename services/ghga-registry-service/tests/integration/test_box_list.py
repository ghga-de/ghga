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

"""Test that MongoDB sorts, filters and pages the list of upload boxes."""

from asyncio import sleep
from datetime import timedelta
from uuid import uuid4

import pytest

from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.http.mock_api import respond
from hexkit.utils import now_utc_ms_prec
from rs.constants import RESEARCH_DATA_UPLOAD_BOX_COLLECTION
from tests.fixtures.joint import JointFixture
from tests.fixtures.utils import TEST_MAX_SIZE

pytestmark = pytest.mark.asyncio


def _auth_context(*, roles: list[str]) -> AuthContext:
    """Make an auth context for a new user with the given roles."""
    iat = now_utc_ms_prec() - timedelta(hours=1)
    return AuthContext(
        id=str(uuid4()),
        name="Test User",
        email="user@test.com",
        iat=iat,
        exp=iat + timedelta(hours=24),
        roles=roles,
    )


async def test_box_list(joint_fixture: JointFixture):
    """Test the order, the filters and the pages of the box list."""
    rdub_manager = joint_fixture.registry.rdub_manager
    ds_auth_context = _auth_context(roles=["data_steward"])
    joint_fixture.file_box_api.on_create_file_upload_box = respond(
        201, json=str(uuid4())
    )
    joint_fixture.file_box_api.on_update_file_upload_box = respond(204)

    box_ids = []
    for i in range(4):
        await sleep(0.002)  # distinct last_changed values, which MongoDB keeps in ms
        box_ids.append(
            await rdub_manager.create_research_data_upload_box(
                title=f"Box {i}",
                description="A box for the box list test",
                storage_alias="test-storage",
                data_steward_id=uuid4(),
                max_size=TEST_MAX_SIZE,
            )
        )
    box = await rdub_manager.get_research_data_upload_box(
        box_id=box_ids[1], auth_context=ds_auth_context
    )
    await rdub_manager.update_research_data_upload_box(
        box_id=box.id,
        version=box.version,
        title=None,
        description=None,
        state="locked",
        auth_context=ds_auth_context,
    )

    # Open boxes first, each state with the most recently changed box first
    results = await rdub_manager.get_research_data_upload_boxes(
        auth_context=ds_auth_context
    )
    assert results.count == 4
    assert [box.id for box in results.boxes] == [
        box_ids[3],
        box_ids[2],
        box_ids[0],
        box_ids[1],
    ]

    results = await rdub_manager.get_research_data_upload_boxes(
        auth_context=ds_auth_context, skip=1, limit=2
    )
    assert results.count == 4
    assert [box.id for box in results.boxes] == [box_ids[2], box_ids[0]]

    results = await rdub_manager.get_research_data_upload_boxes(
        auth_context=ds_auth_context, state="locked"
    )
    assert results.count == 1
    assert [box.id for box in results.boxes] == [box_ids[1]]

    # A user sees only the accessible boxes, skipping a grant for a deleted box
    joint_fixture.access_api.on_get_accessible_upload_boxes = respond(
        200, json=[str(box_ids[0]), str(box_ids[1]), str(uuid4())]
    )
    results = await rdub_manager.get_research_data_upload_boxes(
        auth_context=_auth_context(roles=[]), limit=1
    )
    assert results.count == 2
    assert [box.id for box in results.boxes] == [box_ids[0]]

    # An index serves the sort order
    collection = joint_fixture.mongodb.client[joint_fixture.config.db_name][
        RESEARCH_DATA_UPLOAD_BOX_COLLECTION
    ]
    index_keys = [index["key"] for index in collection.index_information().values()]
    assert [("state", -1), ("last_changed", -1), ("_id", 1)] in index_keys
