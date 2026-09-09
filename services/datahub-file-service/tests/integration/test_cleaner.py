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
"""Integration tests for the S3Cleaner class"""

import unittest.mock

import httpx2
import pytest

from dhfs.ports.outbound.s3 import S3ClientPort
from ghga_service_commons.api.mock_api import fail_to_connect, respond
from hexkit.providers.s3.testutils import temp_file_object
from tests.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio()


@pytest.mark.parametrize(
    "removable_files",
    [
        [
            "18d50867-fbef-4a32-8f70-e81766383980",
            "1969264c-3abe-44e6-8db9-65612d6c6a90",
            "a7084f3d-f4cb-4333-853c-bc1e400f14ba",
        ],
        [
            "18d50867-fbef-4a32-8f70-e81766383980",
            "1969264c-3abe-44e6-8db9-65612d6c6a90",
        ],
        [],
    ],
    ids=["All", "AllButOne", "None"],
)
async def test_cleaner_successful(
    joint_fixture: JointFixture,
    removable_files: list[str],
    caplog,
):
    """Test that files can be removed from the interrogation bucket."""
    # Pre-populate some objects in the interrogation bucket
    interrogation = joint_fixture.config.interrogation_bucket_id
    file_ids = [
        "18d50867-fbef-4a32-8f70-e81766383980",
        "1969264c-3abe-44e6-8db9-65612d6c6a90",
        "a7084f3d-f4cb-4333-853c-bc1e400f14ba",
    ]
    for file_id in file_ids:
        with temp_file_object(bucket_id=interrogation, object_id=str(file_id)) as file:
            await joint_fixture.s3.populate_file_objects([file])

    # Now verify that the expected items appear in the interrogation bucket
    assert set(
        await joint_fixture.s3.storage.list_all_object_ids(interrogation)
    ) == set(file_ids)

    # Create a mock response from the central API
    joint_fixture.central_api.on_get_removable_files = respond(
        200, json=removable_files
    )

    # Run the scan and clean operation
    with caplog.at_level("DEBUG"):
        await joint_fixture.s3_cleaner.scan_and_clean()

    # Verify log messages based on test case
    if removable_files == file_ids:  # "All" test case
        assert "Central API indicated 3 file(s) can be removed." in caplog.text
        assert (
            "Cleanup completed: 3 file(s) deleted successfully, 0 failed."
            in caplog.text
        )
    elif not removable_files:  # "None" test case
        assert "No files marked for removal, exiting." in caplog.text

    # Check that only the removable_files were deleted from the bucket
    remaining_files = await joint_fixture.s3.storage.list_all_object_ids(interrogation)
    assert set(remaining_files) == set(file_ids) - set(removable_files)


async def test_cleaner_some_files_failed(
    joint_fixture: JointFixture,
    caplog,
):
    """Test behavior and logs of cleaner when some files aren't cleaned up properly"""
    # Pre-populate some objects in the interrogation bucket
    interrogation = joint_fixture.config.interrogation_bucket_id
    file_ids = [
        "18d50867-fbef-4a32-8f70-e81766383980",
        "1969264c-3abe-44e6-8db9-65612d6c6a90",
        "a7084f3d-f4cb-4333-853c-bc1e400f14ba",
    ]
    failing_file_id = file_ids[0]

    for file_id in file_ids:
        with temp_file_object(bucket_id=interrogation, object_id=file_id) as file:
            await joint_fixture.s3.populate_file_objects([file])

    assert set(
        await joint_fixture.s3.storage.list_all_object_ids(interrogation)
    ) == set(file_ids)

    # Mock central API to mark all files as removable
    joint_fixture.central_api.on_get_removable_files = respond(200, json=file_ids)

    # Patch remove_file to raise an error for one specific file, letting the others succeed
    original_remove_file = joint_fixture.s3_cleaner._s3_client.remove_file  # type: ignore

    async def failing_remove_file(*, object_id: str) -> None:
        if object_id == failing_file_id:
            raise S3ClientPort.S3CleanupError(
                bucket_id=interrogation, object_id=object_id
            )
        await original_remove_file(object_id=object_id)

    with unittest.mock.patch.object(
        joint_fixture.s3_cleaner._s3_client,  # type: ignore
        "remove_file",
        new=failing_remove_file,
    ):
        with caplog.at_level("INFO"):
            await joint_fixture.s3_cleaner.scan_and_clean()

    # Verify the log reflects the partial failure
    assert (
        "Cleanup completed with errors: 2 file(s) deleted successfully, 1 failed."
        in caplog.text
    )

    # The file that failed to delete should still be in the bucket
    remaining_files = await joint_fixture.s3.storage.list_all_object_ids(interrogation)
    assert set(remaining_files) == {failing_file_id}


async def test_no_files_in_interrogation_bucket(
    joint_fixture: JointFixture,
    caplog,
):
    """Test that the cleaner handles an empty interrogation bucket gracefully."""
    # Don't pre-populate any objects in the interrogation bucket
    interrogation = joint_fixture.config.interrogation_bucket_id
    await joint_fixture.s3.storage.create_bucket(interrogation)

    # Verify the bucket is empty
    assert await joint_fixture.s3.storage.list_all_object_ids(interrogation) == []

    # Verify that the Central API isn't called (should quit)
    def should_not_be_called(
        request: httpx2.Request, **path_variables: str
    ) -> httpx2.Response:
        raise RuntimeError("Was not supposed to call Central API!")

    joint_fixture.central_api.on_get_removable_files = should_not_be_called

    # Run the scan and clean operation - should complete without errors
    with caplog.at_level("INFO"):
        await joint_fixture.s3_cleaner.scan_and_clean()

    # Verify the cleaner logged that no files needed cleanup
    assert "No files to clean up, exiting." in caplog.text


async def test_central_api_error_during_cleanup(
    joint_fixture: JointFixture,
    caplog,
):
    """Test that a non-200 response from get_removable_files is logged explicitly."""
    interrogation = joint_fixture.config.interrogation_bucket_id
    file_id = "18d50867-fbef-4a32-8f70-e81766383980"
    with temp_file_object(bucket_id=interrogation, object_id=file_id) as file:
        await joint_fixture.s3.populate_file_objects([file])

    joint_fixture.central_api.on_get_removable_files = respond(500)

    with caplog.at_level("ERROR"):
        await joint_fixture.s3_cleaner.scan_and_clean()

    assert "The GHGA Central API returned an error response" in caplog.text
    remaining = await joint_fixture.s3.storage.list_all_object_ids(interrogation)
    assert file_id in remaining


async def test_central_api_bad_format_during_cleanup(
    joint_fixture: JointFixture,
    caplog,
):
    """Test that an unparseable response from get_removable_files is logged explicitly."""
    interrogation = joint_fixture.config.interrogation_bucket_id
    file_id = "18d50867-fbef-4a32-8f70-e81766383980"
    with temp_file_object(bucket_id=interrogation, object_id=file_id) as file:
        await joint_fixture.s3.populate_file_objects([file])

    joint_fixture.central_api.on_get_removable_files = respond(
        200, json={"not": "a list"}
    )

    with caplog.at_level("ERROR"):
        await joint_fixture.s3_cleaner.scan_and_clean()

    assert (
        "The GHGA Central API returned an unrecognized response format" in caplog.text
    )
    remaining = await joint_fixture.s3.storage.list_all_object_ids(interrogation)
    assert file_id in remaining


async def test_central_api_unreachable(joint_fixture: JointFixture, caplog):
    """Make sure the S3Cleaner handles Central API connection failures."""
    # Pre-populate some objects in the interrogation bucket
    interrogation = joint_fixture.config.interrogation_bucket_id
    file_ids = [
        "18d50867-fbef-4a32-8f70-e81766383980",
        "1969264c-3abe-44e6-8db9-65612d6c6a90",
    ]
    for file_id in file_ids:
        with temp_file_object(bucket_id=interrogation, object_id=str(file_id)) as file:
            await joint_fixture.s3.populate_file_objects([file])

    joint_fixture.central_api.on_get_removable_files = fail_to_connect()

    with caplog.at_level("ERROR"):
        await joint_fixture.s3_cleaner.scan_and_clean()
    assert "Unable to reach the GHGA Central API" in caplog.text

    # Verify that no files were deleted (operation failed before deletion)
    remaining_files = await joint_fixture.s3.storage.list_all_object_ids(interrogation)
    assert set(remaining_files) == set(file_ids)
