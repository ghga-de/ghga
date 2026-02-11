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

"""Unit tests for the main core class"""

from asyncio import sleep
from dataclasses import dataclass
from datetime import timedelta
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from ghga_service_commons.auth.context import AuthContext
from hexkit.providers.testing.dao import BaseInMemDao, new_mock_dao_class
from hexkit.utils import now_utc_ms_prec

from tests.fixtures import ConfigFixture
from uos.config import Config
from uos.core import models
from uos.core.orchestrator import UploadOrchestrator
from uos.ports.outbound.http import AccessClientPort, FileBoxClientPort

pytestmark = pytest.mark.asyncio

TEST_FILE_UPLOAD_BOX_ID = UUID("2735c960-5e15-45dc-b27a-59162fbb2fd7")
TEST_DS_ID = UUID("f698158d-8417-4368-bb45-349277bc45ee")
TEST_USER_ID1 = UUID("0ef5e39b-3ff2-4685-99e8-5aaf04942c45")

# Auth context constants for testing
DATA_STEWARD_AUTH_CONTEXT = Mock(spec=AuthContext)
DATA_STEWARD_AUTH_CONTEXT.id = str(TEST_DS_ID)
DATA_STEWARD_AUTH_CONTEXT.roles = ["data_steward"]

USER1_AUTH_CONTEXT = Mock(spec=AuthContext)
USER1_AUTH_CONTEXT.id = str(TEST_USER_ID1)
USER1_AUTH_CONTEXT.roles = []

InMemBoxDao = new_mock_dao_class(dto_model=models.ResearchDataUploadBox, id_field="id")
InMemAccessionMapDao = new_mock_dao_class(
    dto_model=models.AccessionMap, id_field="box_id"
)


@dataclass
class JointRig:
    """Test fixture containing all components needed for controller testing."""

    config: Config
    box_dao: BaseInMemDao[models.ResearchDataUploadBox]
    accession_map_dao: BaseInMemDao[models.AccessionMap]
    file_upload_box_client: FileBoxClientPort
    access_client: AccessClientPort
    controller: UploadOrchestrator


async def file_upload_box_id_generator(*args, **kwargs) -> UUID:
    """Return a new FileUploadBox ID"""
    return uuid4()


@pytest.fixture()
def rig(config: ConfigFixture) -> JointRig:
    """Return a joint fixture with in-memory dependency mocks"""
    _config = config.config
    file_box_client_mock = AsyncMock()
    file_box_client_mock.create_file_upload_box = file_upload_box_id_generator
    access_client_mock = AsyncMock()

    controller = UploadOrchestrator(
        box_dao=(box_dao := InMemBoxDao()),  # type: ignore
        accession_map_dao=(accession_map_dao := InMemAccessionMapDao()),  # type: ignore
        file_upload_box_client=file_box_client_mock,
        access_client=access_client_mock,
        audit_repository=AsyncMock(),
    )

    return JointRig(
        config=_config,
        box_dao=box_dao,
        accession_map_dao=accession_map_dao,
        file_upload_box_client=file_box_client_mock,
        access_client=access_client_mock,
        controller=controller,
    )


@pytest_asyncio.fixture(name="populated_boxes")
async def populate_boxes(rig: JointRig):
    """Populate 5 test boxes in the JointRig's mock DAO"""
    # Create multiple boxes for testing
    box_ids: list[UUID] = []
    for i in range(5):
        box_id = await rig.controller.create_research_data_upload_box(
            title=f"Box {chr(65 + i)}",  # "Box A", "Box B", etc.
            description=f"Description {i}",
            storage_alias="HD01",
            data_steward_id=TEST_DS_ID,
        )
        await sleep(0.001)  # insert pause to ensure different timestamps for sorting
        box_ids.append(box_id)
    return box_ids


async def test_create_research_data_upload_box(rig: JointRig):
    """Test the normal path of creating a research data upload box."""
    box_id = await rig.controller.create_research_data_upload_box(
        title="Test",
        description="Just a test",
        storage_alias="HD01",
        data_steward_id=TEST_DS_ID,
    )

    box = rig.box_dao.latest
    assert box.id == box_id
    assert box.title == "Test"
    assert box.description == "Just a test"
    assert box.storage_alias == "HD01"
    assert box.changed_by == TEST_DS_ID
    assert box.file_count == 0
    assert box.size == 0
    assert isinstance(box.file_upload_box_id, UUID)
    assert box.last_changed - now_utc_ms_prec() < timedelta(seconds=5)
    assert box.state == "open"
    assert box.file_upload_box_state == "open"


async def test_update_research_data_upload_box_happy(
    rig: JointRig, populated_boxes: list[UUID]
):
    """Test the normal path of updating box attributes."""
    # Mock the access client to return that the user has access
    rig.access_client.check_box_access.return_value = True  # type: ignore

    # Get the box to get its current version
    box_id = populated_boxes[0]
    box = await rig.box_dao.get_by_id(box_id)

    # Create an update request
    update_request = models.UpdateUploadBoxRequest(
        version=box.version, title="Updated Title", description="Updated Description"
    )

    # Call the update method
    await rig.controller.update_research_data_upload_box(
        box_id=box_id, request=update_request, auth_context=DATA_STEWARD_AUTH_CONTEXT
    )

    # Verify the box was updated
    updated_box = await rig.box_dao.get_by_id(box_id)
    assert updated_box.title == "Updated Title"
    assert updated_box.description == "Updated Description"
    assert updated_box.changed_by == TEST_DS_ID
    assert updated_box.last_changed - now_utc_ms_prec() < timedelta(seconds=5)

    # Verify access client was not used because user is a Data Steward
    rig.access_client.check_box_access.assert_not_called()  # type: ignore


async def test_update_research_data_upload_box_unauthorized(
    rig: JointRig, populated_boxes: list[UUID]
):
    """Test the scenario where a user tries updating box attributes like title or description.

    Regular users are not authorized to do this, so this should be blocked.
    """
    # Mock the access client to return that the user has access (but box doesn't exist)
    rig.access_client.check_box_access.return_value = True  # type: ignore

    # Create an update request
    box_id = populated_boxes[0]
    box = await rig.box_dao.get_by_id(box_id)

    update_request = models.UpdateUploadBoxRequest(
        version=box.version, title="Updated Title", description="Updated Description"
    )

    # Call the update method
    with pytest.raises(rig.controller.BoxAccessError):
        await rig.controller.update_research_data_upload_box(
            box_id=box_id,
            request=update_request,
            auth_context=USER1_AUTH_CONTEXT,
        )


async def test_update_research_data_upload_box_not_found(rig: JointRig):
    """Test the box not found error case in the update method."""
    # Mock the access client to return that the user has access (but box doesn't exist)
    rig.access_client.check_box_access.return_value = True  # type: ignore

    # Create an update request
    update_request = models.UpdateUploadBoxRequest(
        version=0, title="Updated Title", description="Updated Description"
    )

    # Try to update a non-existent box ID
    non_existent_box_id = uuid4()

    # This should raise BoxNotFoundError since the box doesn't exist
    with pytest.raises(rig.controller.BoxNotFoundError):
        await rig.controller.update_research_data_upload_box(
            box_id=non_existent_box_id,
            request=update_request,
            auth_context=DATA_STEWARD_AUTH_CONTEXT,
        )


async def test_get_upload_box_files_happy(rig: JointRig, populated_boxes: list[UUID]):
    """Test the normal path of getting a list of FileUpload objects for a box from the file box service."""
    # Mock the file box client to return a list of FileUpload objects
    test_file_uploads = [
        models.FileUploadWithAccession(
            id=uuid4(),
            box_id=TEST_FILE_UPLOAD_BOX_ID,
            storage_alias="HD01",
            bucket_id="inbox",
            alias=f"test{i}",
            decrypted_sha256=f"checksum{i}",
            decrypted_size=1000 + i * 100,
            part_size=100,
            state="archived",
            state_updated=now_utc_ms_prec(),
        )
        for i in range(3)
    ]
    # Sort by alias as expected by the orchestrator
    test_file_uploads_sorted = sorted(test_file_uploads, key=lambda x: x.alias)
    rig.file_upload_box_client.get_file_upload_list.return_value = test_file_uploads  # type: ignore

    # Mock the access client for non-data steward case
    box_id = populated_boxes[0]
    rig.access_client.check_box_access.return_value = [box_id]  # type: ignore

    # Call the method
    result = await rig.controller.get_upload_box_files(
        box_id=box_id, auth_context=USER1_AUTH_CONTEXT
    )

    # Verify the results are sorted by alias
    assert result == test_file_uploads_sorted

    # Verify the file box client was called
    rig.file_upload_box_client.get_file_upload_list.assert_called_once()  # type: ignore

    # Verify access check was performed for non-data steward
    rig.access_client.check_box_access.assert_called_once()  # type: ignore


async def test_get_upload_box_files_access_error(
    rig: JointRig, populated_boxes: list[UUID]
):
    """Test the case where getting box files fails because the user doesn't have access."""
    # Mock the access client to return that the user does NOT have access to this box
    rig.access_client.check_box_access.return_value = False  # type: ignore

    # This should raise BoxAccessError since the user doesn't have access
    with pytest.raises(rig.controller.BoxAccessError):
        await rig.controller.get_upload_box_files(
            box_id=populated_boxes[0], auth_context=USER1_AUTH_CONTEXT
        )

    # Verify that access check was performed
    rig.access_client.check_box_access.assert_called_once()  # type: ignore

    # Verify that file box client was NOT called since access was denied
    rig.file_upload_box_client.get_file_upload_list.assert_not_called()  # type: ignore


async def test_get_upload_box_files_box_not_found(rig: JointRig):
    """Test the case where getting box files fails because the box doesn't exist."""
    # Try to get files from a non-existent box ID
    non_existent_box_id = uuid4()

    # This should raise BoxNotFoundError since the box doesn't exist
    # The error comes from the initial get_by_id call in get_upload_box_files
    with pytest.raises(rig.controller.BoxNotFoundError):
        await rig.controller.get_upload_box_files(
            box_id=non_existent_box_id, auth_context=DATA_STEWARD_AUTH_CONTEXT
        )

    # Verify that access client was NOT called since the box lookup failed first
    rig.access_client.get_accessible_upload_boxes.assert_not_called()  # type: ignore

    # Verify that file box client was NOT called since the box lookup failed
    rig.file_upload_box_client.get_file_upload_list.assert_not_called()  # type: ignore


async def test_upsert_file_upload_box_happy(rig: JointRig, populated_boxes: list[UUID]):
    """Test the method that consumes FileUploadBox data and uses it to update RDUBoxes."""
    # Get the created box to verify initial state
    box_id = populated_boxes[0]
    initial_box = await rig.box_dao.get_by_id(box_id)
    assert initial_box.file_count == 0
    assert initial_box.size == 0
    assert initial_box.version == 0
    assert initial_box.file_upload_box_version == 0
    assert initial_box.file_upload_box_state == "open"
    file_upload_box_id = initial_box.file_upload_box_id

    # Create a FileUploadBox with updated data
    updated_file_upload_box = models.FileUploadBox(
        id=file_upload_box_id,  # This should match the file_upload_box_id in our research box
        version=1,
        state="locked",
        file_count=5,
        size=1024000,
        storage_alias="HD01",
    )

    # Call upsert_file_upload_box
    await rig.controller.upsert_file_upload_box(updated_file_upload_box)

    # Verify the research data upload box was updated
    updated_box = await rig.box_dao.get_by_id(box_id)
    assert updated_box.version == 1
    assert updated_box.file_count == 5
    assert updated_box.size == 1024000
    assert updated_box.file_upload_box_version == 1
    assert updated_box.file_upload_box_state == "locked"

    # Verify other fields remain unchanged
    assert updated_box.title == "Box A"
    assert updated_box.description == "Description 0"
    assert updated_box.storage_alias == "HD01"


async def test_upsert_file_upload_box_not_found(rig: JointRig):
    """Test the edge case where a matching Research Data Upload Box doesn't exist."""
    # Create a FileUploadBox with a random ID
    orphaned_file_upload_box = models.FileUploadBox(
        id=uuid4(),
        version=0,
        state="open",
        file_count=3,
        size=512000,
        storage_alias="HD02",
    )

    # This should not raise an error, just log and continue
    await rig.controller.upsert_file_upload_box(orphaned_file_upload_box)

    # Verify nothing was inserted in the DB
    assert not [x async for x in rig.box_dao.find_all(mapping={})]


async def test_get_research_data_upload_box_happy(
    rig: JointRig, populated_boxes: list[UUID]
):
    """Test the normal path of getting a research data upload box."""
    # Try retrieval with Data Steward credentials
    rig.access_client.check_box_access.return_value = True  # type: ignore
    box_id = populated_boxes[0]
    result = await rig.controller.get_research_data_upload_box(
        box_id=box_id, auth_context=DATA_STEWARD_AUTH_CONTEXT
    )

    # Verify we got the correct box back
    assert result.id == box_id
    assert result.title == "Box A"
    assert result.description == "Description 0"
    assert result.storage_alias == "HD01"
    assert result.changed_by == TEST_DS_ID

    # Verify access check was NOT called for Data Steward
    rig.access_client.check_box_access.assert_not_called()  # type: ignore

    # Try with regular user
    rig.access_client.check_box_access.return_value = True  # type: ignore
    result = await rig.controller.get_research_data_upload_box(
        box_id=box_id, auth_context=USER1_AUTH_CONTEXT
    )
    rig.access_client.check_box_access.assert_called_once()  # type: ignore


async def test_get_research_data_upload_box_access_denied(
    rig: JointRig, populated_boxes: list[UUID]
):
    """Test the case where the user doesn't have access to the box."""
    # Mock the access client to return that the user does NOT have access
    rig.access_client.check_box_access.return_value = False  # type: ignore

    # Try to get the box with a different user
    # This should raise BoxAccessError since the user doesn't have access
    with pytest.raises(rig.controller.BoxAccessError):
        await rig.controller.get_research_data_upload_box(
            box_id=populated_boxes[0], auth_context=USER1_AUTH_CONTEXT
        )

    # Verify access check was called
    rig.access_client.check_box_access.assert_called_once()  # type: ignore


async def test_get_research_data_upload_box_not_found(rig: JointRig):
    """Test the case where the research data upload box doesn't exist."""
    # Mock the access client to return that the user has access
    rig.access_client.check_box_access.return_value = True  # type: ignore

    # Try to get a non-existent box
    non_existent_box_id = uuid4()

    # This should raise BoxNotFoundError since the box doesn't exist
    with pytest.raises(rig.controller.BoxNotFoundError):
        await rig.controller.get_research_data_upload_box(
            box_id=non_existent_box_id, auth_context=USER1_AUTH_CONTEXT
        )

    # Verify access check was called first
    rig.access_client.check_box_access.assert_called_once()  # type: ignore


async def test_get_upload_access_grants_happy(
    rig: JointRig, populated_boxes: list[UUID]
):
    """Test the normal path for getting upload access grants."""
    # Create mock upload grants that would be returned by access client
    test_iva_id = uuid4()
    mock_grants = [
        models.UploadGrant(
            id=uuid4(),
            user_id=TEST_USER_ID1,
            iva_id=test_iva_id,
            box_id=populated_boxes[i],  # one grant for each box
            created=now_utc_ms_prec(),
            valid_from=now_utc_ms_prec(),
            valid_until=now_utc_ms_prec() + timedelta(days=i),  # push out validity
            user_name="Test User",
            user_email="test@example.com",
            user_title="Dr.",
        )
        for i in range(len(populated_boxes))
    ]

    # Mock the access client to return these grants
    rig.access_client.get_upload_access_grants.return_value = mock_grants  # type: ignore

    # Call the method
    results = await rig.controller.get_upload_access_grants(
        user_id=TEST_USER_ID1,
        iva_id=test_iva_id,
        box_id=None,
        valid=True,
    )

    # Verify the results
    assert len(results) == 5
    result_ids = [grant.box_id for grant in results]
    assert result_ids == list(reversed(populated_boxes))

    # Verify access client was called with correct parameters
    rig.access_client.get_upload_access_grants.assert_called_once_with(  # type: ignore
        user_id=TEST_USER_ID1,
        iva_id=test_iva_id,
        box_id=None,
        valid=True,
    )


async def test_get_upload_access_grants_box_missing(
    rig: JointRig, caplog, populated_boxes: list[UUID]
):
    """Test the case where grants returned from the access API include a grant with
    a box ID that doesn't exist in the UOS. This test also checks that we emit a
    WARNING log (but don't raise an error).
    """
    # Create mock upload grants - one with a valid box ID, one with an invalid box ID
    valid_box_id = populated_boxes[0]
    invalid_box_id = uuid4()  # This box doesn't/won't exist

    mock_grants = [
        models.UploadGrant(
            id=uuid4(),
            user_id=TEST_USER_ID1,
            iva_id=uuid4(),
            box_id=valid_box_id,  # This box exists
            created=now_utc_ms_prec(),
            valid_from=now_utc_ms_prec(),
            valid_until=now_utc_ms_prec() + timedelta(days=7),
            user_name="Test User",
            user_email="test@example.com",
            user_title="Dr.",
        ),
        models.UploadGrant(
            id=uuid4(),
            user_id=TEST_USER_ID1,
            iva_id=uuid4(),
            box_id=invalid_box_id,  # This box doesn't exist
            created=now_utc_ms_prec(),
            valid_from=now_utc_ms_prec(),
            valid_until=now_utc_ms_prec() + timedelta(days=7),
            user_name="Test User 2",
            user_email="test2@example.com",
            user_title="Prof.",
        ),
    ]

    # Mock the access client to return these grants
    rig.access_client.get_upload_access_grants.return_value = mock_grants  # type: ignore

    # Call the method
    result = await rig.controller.get_upload_access_grants()

    # Verify the results - should only contain the grant with the valid box
    assert len(result) == 1
    grant_with_info = result[0]
    assert grant_with_info.box_id == valid_box_id
    assert grant_with_info.box_title == "Box A"
    assert grant_with_info.box_description == "Description 0"

    # Verify a warning was logged for the invalid box
    assert caplog.records
    warning_messages = [
        record.message for record in caplog.records if record.levelname == "WARNING"
    ]
    assert len(warning_messages) >= 1
    assert any(str(invalid_box_id) in msg for msg in warning_messages)
    assert any("doesn't exist in UOS" in msg for msg in warning_messages)

    # Verify access client was called
    rig.access_client.get_upload_access_grants.assert_called_once()  # type: ignore


async def test_get_boxes_data_steward(rig: JointRig, populated_boxes: list[UUID]):
    """Test the get_research_data_upload_boxes method for data stewards."""
    results = await rig.controller.get_research_data_upload_boxes(
        auth_context=DATA_STEWARD_AUTH_CONTEXT
    )
    assert results.count == 5
    assert len(results.boxes) == 5


async def test_get_boxes_regular_user(rig: JointRig, populated_boxes: list[UUID]):
    """Test the get_research_data_upload_boxes method for users."""
    # Assert that, before being given access, the user gets an empty list
    rig.access_client.get_accessible_upload_boxes.return_value = []  # type: ignore
    results = await rig.controller.get_research_data_upload_boxes(
        auth_context=USER1_AUTH_CONTEXT
    )
    assert results.count == 0
    assert results.boxes == []

    # Give User1 access boxes 1-3 and check results
    rig.access_client.get_accessible_upload_boxes.return_value = populated_boxes[:3]  # type: ignore

    results = await rig.controller.get_research_data_upload_boxes(
        auth_context=USER1_AUTH_CONTEXT
    )
    assert results.count == 3
    result_ids = [box.id for box in results.boxes]
    assert len(result_ids) == 3
    assert result_ids == list(reversed(populated_boxes[:3]))

    # Try retrieving boxes when there's no access
    rig.access_client.get_accessible_upload_boxes.return_value = []  # type: ignore
    results = await rig.controller.get_research_data_upload_boxes(
        auth_context=USER1_AUTH_CONTEXT
    )
    assert results.count == 0
    assert results.boxes == []


async def test_get_boxes_sorting(rig: JointRig, populated_boxes: list[UUID]):
    """Test the sorting within the get_research_data_upload_boxes method.

    Boxes are sorted first by unlocked, then locked boxes, and further sorted by
    most recently changed and finally by box ID (ascending).
    """
    # Update two boxes to have the locked flag set
    locked_box_ids = [populated_boxes[1], populated_boxes[3]]
    for box_id in locked_box_ids:
        await sleep(0.001)
        box = await rig.box_dao.get_by_id(box_id)
        await rig.controller.update_research_data_upload_box(
            box_id=box_id,
            request=models.UpdateUploadBoxRequest(version=box.version, state="locked"),
            auth_context=DATA_STEWARD_AUTH_CONTEXT,
        )

    results = await rig.controller.get_research_data_upload_boxes(
        auth_context=DATA_STEWARD_AUTH_CONTEXT
    )
    assert results.count == 5
    results_ids = [box.id for box in results.boxes]
    assert results_ids == [
        populated_boxes[4],  # Last created, unlocked
        populated_boxes[2],  # Unlocked
        populated_boxes[0],  # Unlocked, created first
        populated_boxes[3],  # Locked, updated most recently
        populated_boxes[1],  # Locked
    ]

    # Filter by locked
    locked_results = await rig.controller.get_research_data_upload_boxes(
        auth_context=DATA_STEWARD_AUTH_CONTEXT, state="locked"
    )
    assert locked_results.count == 2
    locked_results_ids = [box.id for box in locked_results.boxes]
    assert locked_results_ids == [populated_boxes[3], populated_boxes[1]]

    # Filter by open
    unlocked_results = await rig.controller.get_research_data_upload_boxes(
        auth_context=DATA_STEWARD_AUTH_CONTEXT, state="open"
    )
    assert unlocked_results.count == 3
    unlocked_results_ids = [box.id for box in unlocked_results.boxes]
    assert unlocked_results_ids == [
        populated_boxes[4],
        populated_boxes[2],
        populated_boxes[0],
    ]


async def test_get_boxes_pagination(rig: JointRig, populated_boxes: list[UUID]):
    """Test pagination of the get_research_data_upload_boxes method."""
    # Verify pagination works
    results = await rig.controller.get_research_data_upload_boxes(
        auth_context=DATA_STEWARD_AUTH_CONTEXT, skip=2, limit=2
    )
    assert results.count == 5  # Total count is still 5
    assert len(results.boxes) == 2  # But we only get 2 items
    results_ids = [box.id for box in results.boxes]
    assert results_ids == [populated_boxes[2], populated_boxes[1]]  # sorted results

    results = await rig.controller.get_research_data_upload_boxes(
        auth_context=DATA_STEWARD_AUTH_CONTEXT, skip=6, limit=None
    )
    assert results.count == 5
    assert results.boxes == []

    results = await rig.controller.get_research_data_upload_boxes(
        auth_context=DATA_STEWARD_AUTH_CONTEXT, skip=6, limit=1
    )
    assert results.count == 5
    assert results.boxes == []

    # The following won't happen in the real world because all requests go through API
    results = await rig.controller.get_research_data_upload_boxes(
        auth_context=DATA_STEWARD_AUTH_CONTEXT, skip=-1, limit=-1
    )
    assert results.count == 5
    assert len(results.boxes) == 5


async def test_update_accession_map_happy(rig: JointRig, populated_boxes: list[UUID]):
    """Test the normal path of updating an accession map.

    This test also checks for the BoxNotFoundError case, since that is small enough
    to include here.
    """
    box_id = populated_boxes[0]

    # Create test file uploads
    test_file_ids = [uuid4() for _ in range(3)]
    test_file_uploads = [
        models.FileUploadWithAccession(
            id=file_id,
            box_id=TEST_FILE_UPLOAD_BOX_ID,
            storage_alias="HD01",
            bucket_id="inbox",
            alias=f"test{i}",
            decrypted_sha256=f"checksum{i}",
            decrypted_size=1000 + i * 100,
            part_size=100,
            state="awaiting_archival",
            state_updated=now_utc_ms_prec(),
        )
        for i, file_id in enumerate(test_file_ids)
    ]

    # Mock the file box client
    rig.file_upload_box_client.get_file_upload_list.return_value = test_file_uploads  # type: ignore

    # Create an accession map
    accession_map = models.AccessionMapRequest(
        version=0,
        mapping={
            "GHGA001": test_file_ids[0],
            "GHGA002": test_file_ids[1],
            "GHGA003": test_file_ids[2],
        },
    )

    # Verify that a BoxNotFoundError is raised for a non-existent box
    with pytest.raises(rig.controller.BoxNotFoundError):
        await rig.controller.update_accession_map(box_id=uuid4(), request=accession_map)

    # Verify file box client was not called
    rig.file_upload_box_client.get_file_upload_list.assert_not_called()  # type: ignore

    # Get current box ID
    box = await rig.box_dao.get_by_id(box_id)
    version_pre_update = box.version

    # Call the method with the valid map now
    await rig.controller.update_accession_map(box_id=box_id, request=accession_map)

    # Verify the accession map was stored
    stored_map = await rig.accession_map_dao.get_by_id(box_id)
    assert stored_map.box_id == box_id
    assert len(stored_map.mapping) == 3

    # Verify the research data upload box version was incremented
    box = await rig.box_dao.get_by_id(box_id)
    assert box.version - version_pre_update == 1

    # Verify file box client was called
    rig.file_upload_box_client.get_file_upload_list.assert_called_once()  # type: ignore


async def test_update_accession_map_invalid_or_unmapped_file_ids(
    rig: JointRig, populated_boxes: list[UUID]
):
    """Test that invalid file IDs in an accession map or leaving any box files unmapped
    triggers an AccessionMapError.
    """
    box_id = populated_boxes[0]

    # Create test file uploads
    test_file_ids = [uuid4() for _ in range(2)]
    test_file_uploads = [
        models.FileUploadWithAccession(
            id=file_id,
            box_id=TEST_FILE_UPLOAD_BOX_ID,
            storage_alias="HD01",
            bucket_id="inbox",
            alias=f"test{i}",
            decrypted_sha256=f"checksum{i}",
            decrypted_size=1000,
            part_size=100,
            state="awaiting_archival",
            state_updated=now_utc_ms_prec(),
        )
        for i, file_id in enumerate(test_file_ids)
    ]

    # Mock the file box client
    rig.file_upload_box_client.get_file_upload_list.return_value = test_file_uploads  # type: ignore

    # Create an accession map with a file ID that doesn't exist in the box
    invalid_file_id = uuid4()
    accession_map = models.AccessionMapRequest(
        version=0, mapping={"GHGA001": test_file_ids[0], "GHGA002": invalid_file_id}
    )

    # Should raise AccessionMapError
    with pytest.raises(rig.controller.AccessionMapError, match="not in the box"):
        await rig.controller.update_accession_map(box_id=box_id, request=accession_map)

    # Verify file box client was called
    rig.file_upload_box_client.get_file_upload_list.assert_called_once()  # type: ignore

    # Create an accession map that omits a file
    accession_map = models.AccessionMapRequest(
        version=0, mapping={"GHGA001": test_file_ids[0]}
    )

    # Should raise AccessionMapError
    with pytest.raises(
        rig.controller.AccessionMapError, match="still need to be mapped"
    ):
        await rig.controller.update_accession_map(box_id=box_id, request=accession_map)


async def test_update_accession_map_filters_cancelled_and_failed(
    rig: JointRig, populated_boxes: list[UUID]
):
    """Test that cancelled and failed files are filtered out when validating accession map."""
    box_id = populated_boxes[0]

    # Create test file uploads including cancelled and failed ones
    test_file_ids = [uuid4() for _ in range(4)]
    test_file_uploads = [
        models.FileUploadWithAccession(
            id=test_file_ids[0],
            box_id=TEST_FILE_UPLOAD_BOX_ID,
            storage_alias="HD01",
            bucket_id="inbox",
            alias="test0",
            decrypted_sha256="checksum0",
            decrypted_size=1000,
            part_size=100,
            state="awaiting_archival",
            state_updated=now_utc_ms_prec(),
        ),
        models.FileUploadWithAccession(
            id=test_file_ids[1],
            box_id=TEST_FILE_UPLOAD_BOX_ID,
            storage_alias="HD01",
            bucket_id="inbox",
            alias="test1",
            decrypted_sha256="checksum1",
            decrypted_size=1000,
            part_size=100,
            state="cancelled",  # This should be filtered out
            state_updated=now_utc_ms_prec(),
        ),
        models.FileUploadWithAccession(
            id=test_file_ids[2],
            box_id=TEST_FILE_UPLOAD_BOX_ID,
            storage_alias="HD01",
            bucket_id="inbox",
            alias="test2",
            decrypted_sha256="checksum2",
            decrypted_size=1000,
            part_size=100,
            state="failed",  # This should be filtered out
            state_updated=now_utc_ms_prec(),
        ),
        models.FileUploadWithAccession(
            id=test_file_ids[3],
            box_id=TEST_FILE_UPLOAD_BOX_ID,
            storage_alias="HD01",
            bucket_id="inbox",
            alias="test3",
            decrypted_sha256="checksum3",
            decrypted_size=1000,
            part_size=100,
            state="awaiting_archival",
            state_updated=now_utc_ms_prec(),
        ),
    ]

    # Mock the file box client
    rig.file_upload_box_client.get_file_upload_list.return_value = test_file_uploads  # type: ignore

    # Create an accession map for only the valid files
    request = models.AccessionMapRequest(
        version=0, mapping={"GHGA001": test_file_ids[0], "GHGA004": test_file_ids[3]}
    )

    # This should succeed because cancelled and failed files are ignored
    await rig.controller.update_accession_map(box_id=box_id, request=request)

    # Verify the accession map was stored
    stored_map = await rig.accession_map_dao.get_by_id(box_id)
    assert len(stored_map.mapping) == 2


async def test_archive_research_data_upload_box_happy(
    rig: JointRig, populated_boxes: list[UUID]
):
    """Test the normal path of archiving a research data upload box."""
    box_id = populated_boxes[0]

    # Lock the box first
    box = await rig.box_dao.get_by_id(box_id)
    box.state = "locked"
    box.version = 1
    await rig.box_dao.update(box)

    # Create test file uploads
    test_file_ids = [uuid4() for _ in range(2)]
    test_file_uploads = [
        models.FileUploadWithAccession(
            id=file_id,
            box_id=TEST_FILE_UPLOAD_BOX_ID,
            storage_alias="HD01",
            bucket_id="inbox",
            alias=f"test{i}",
            decrypted_sha256=f"checksum{i}",
            decrypted_size=1000,
            part_size=100,
            state="awaiting_archival",
            state_updated=now_utc_ms_prec(),
        )
        for i, file_id in enumerate(test_file_ids)
    ]

    # Mock the file box client
    rig.file_upload_box_client.get_file_upload_list.return_value = test_file_uploads  # type: ignore
    rig.file_upload_box_client.archive_file_upload_box = AsyncMock()  # type: ignore

    # Create an accession map
    accession_map = models.AccessionMap(
        box_id=box_id,
        mapping={"GHGA001": test_file_ids[0], "GHGA002": test_file_ids[1]},
    )
    await rig.accession_map_dao.insert(accession_map)

    # Archive the box via update
    update_request = models.UpdateUploadBoxRequest(version=1, state="archived")

    await rig.controller.update_research_data_upload_box(
        box_id=box_id,
        request=update_request,
        auth_context=DATA_STEWARD_AUTH_CONTEXT,
    )

    # Verify the box was updated
    updated_box = await rig.box_dao.get_by_id(box_id)
    assert updated_box.state == "archived"
    assert updated_box.version == 2
    assert updated_box.file_upload_box_state == "archived"
    assert updated_box.file_upload_box_version == 1
    assert updated_box.changed_by == TEST_DS_ID

    # Verify file box client was called to archive
    rig.file_upload_box_client.archive_file_upload_box.assert_called_once()


async def test_archive_via_update_box_not_found(rig: JointRig):
    """Test that archiving a non-existent box raises BoxNotFoundError."""
    non_existent_box_id = uuid4()

    update_request = models.UpdateUploadBoxRequest(version=0, state="archived")

    # This should raise BoxNotFoundError
    with pytest.raises(rig.controller.BoxNotFoundError):
        await rig.controller.update_research_data_upload_box(
            box_id=non_existent_box_id,
            request=update_request,
            auth_context=DATA_STEWARD_AUTH_CONTEXT,
        )


async def test_update_box_outdated_version(rig: JointRig, populated_boxes: list[UUID]):
    """Test that updating with outdated version info raises VersionError."""
    box_id = populated_boxes[0]

    # Update the box version in the database
    box = await rig.box_dao.get_by_id(box_id)
    box.version = 5
    await rig.box_dao.update(box)

    # Try to update with outdated version
    update_request = models.UpdateUploadBoxRequest(
        version=3,  # Outdated!
        title="New Title",
    )

    with pytest.raises(rig.controller.VersionError, match="has changed"):
        await rig.controller.update_research_data_upload_box(
            box_id=box_id,
            request=update_request,
            auth_context=DATA_STEWARD_AUTH_CONTEXT,
        )


async def test_archive_box_not_locked(rig: JointRig, populated_boxes: list[UUID]):
    """Test that archiving an unlocked box raises StateChangeError."""
    box_id = populated_boxes[0]

    # Get the box (should be in 'open' state)
    box = await rig.box_dao.get_by_id(box_id)
    assert box.state == "open"

    # Try to archive without locking first (invalid state transition)
    update_request = models.UpdateUploadBoxRequest(
        version=box.version, state="archived"
    )

    with pytest.raises(
        rig.controller.StateChangeError,
        match="cannot be changed from 'open' to 'archived'",
    ):
        await rig.controller.update_research_data_upload_box(
            box_id=box_id,
            request=update_request,
            auth_context=DATA_STEWARD_AUTH_CONTEXT,
        )


async def test_archive_box_no_accession_map(rig: JointRig, populated_boxes: list[UUID]):
    """Test that archiving without an accession map raises ArchivalPrereqsError."""
    box_id = populated_boxes[0]

    # Lock the box
    box = await rig.box_dao.get_by_id(box_id)
    box.state = "locked"
    await rig.box_dao.update(box)

    # Try to archive without creating an accession map
    update_request = models.UpdateUploadBoxRequest(
        version=box.version, state="archived"
    )

    with pytest.raises(rig.controller.ArchivalPrereqsError, match="not been assigned"):
        await rig.controller.update_research_data_upload_box(
            box_id=box_id,
            request=update_request,
            auth_context=DATA_STEWARD_AUTH_CONTEXT,
        )


async def test_archive_box_missing_accessions(
    rig: JointRig, populated_boxes: list[UUID]
):
    """Test that archiving with missing accessions raises ArchivalPrereqsError."""
    box_id = populated_boxes[0]

    # Lock the box
    box = await rig.box_dao.get_by_id(box_id)
    box.state = "locked"
    await rig.box_dao.update(box)

    # Create 3 test file uploads
    test_file_ids = [uuid4() for _ in range(3)]
    test_file_uploads = [
        models.FileUploadWithAccession(
            id=file_id,
            box_id=TEST_FILE_UPLOAD_BOX_ID,
            storage_alias="HD01",
            bucket_id="inbox",
            alias=f"test{i}",
            decrypted_sha256=f"checksum{i}",
            decrypted_size=1000,
            part_size=100,
            state="awaiting_archival",
            state_updated=now_utc_ms_prec(),
        )
        for i, file_id in enumerate(test_file_ids)
    ]

    # Mock the file box client to return the file uploads
    rig.file_upload_box_client.get_file_upload_list.return_value = test_file_uploads  # type: ignore

    # Create an incomplete accession map (missing the third file)
    accession_map = models.AccessionMap(
        box_id=box_id,
        mapping={"GHGA001": test_file_ids[0], "GHGA002": test_file_ids[1]},
    )
    await rig.accession_map_dao.insert(accession_map)

    # Try to archive with missing accessions
    update_request = models.UpdateUploadBoxRequest(
        version=box.version, state="archived"
    )

    with pytest.raises(
        rig.controller.ArchivalPrereqsError, match="missing an accession"
    ):
        await rig.controller.update_research_data_upload_box(
            box_id=box_id,
            request=update_request,
            auth_context=DATA_STEWARD_AUTH_CONTEXT,
        )


async def test_archive_box_file_upload_box_version_error(
    rig: JointRig, populated_boxes: list[UUID]
):
    """Test that a FileUploadBox version error during archival raises VersionError and rolls back."""
    box_id = populated_boxes[0]

    # Lock the box
    box = await rig.box_dao.get_by_id(box_id)
    box.state = "locked"
    original_version = box.version
    await rig.box_dao.update(box)

    # Create test file uploads
    test_file_ids = [uuid4()]
    test_file_uploads = [
        models.FileUploadWithAccession(
            id=test_file_ids[0],
            box_id=TEST_FILE_UPLOAD_BOX_ID,
            storage_alias="HD01",
            bucket_id="inbox",
            alias="test0",
            decrypted_sha256="checksum0",
            decrypted_size=1000,
            part_size=100,
            state="awaiting_archival",
            state_updated=now_utc_ms_prec(),
        )
    ]

    # Mock the file box client
    rig.file_upload_box_client.get_file_upload_list.return_value = test_file_uploads  # type: ignore
    rig.file_upload_box_client.archive_file_upload_box = AsyncMock(  # type: ignore
        side_effect=FileBoxClientPort.FUBVersionError("Version mismatch")
    )

    # Create an accession map
    accession_map = models.AccessionMap(
        box_id=box_id, mapping={"GHGA001": test_file_ids[0]}
    )
    await rig.accession_map_dao.insert(accession_map)

    # Try to archive - should raise VersionError due to FUB version mismatch
    update_request = models.UpdateUploadBoxRequest(
        version=box.version, state="archived"
    )

    with pytest.raises(rig.controller.VersionError, match="out of date"):
        await rig.controller.update_research_data_upload_box(
            box_id=box_id,
            request=update_request,
            auth_context=DATA_STEWARD_AUTH_CONTEXT,
        )

    # Verify the box state was rolled back
    unchanged_box = await rig.box_dao.get_by_id(box_id)
    assert unchanged_box.state == "locked"  # Still locked, not archived
    assert unchanged_box.version == original_version  # Version rolled back
