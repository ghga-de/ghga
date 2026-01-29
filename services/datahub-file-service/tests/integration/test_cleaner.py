# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

import httpx
import pytest
from hexkit.providers.s3.testutils import temp_file_object
from pytest_httpx import HTTPXMock

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
    httpx_mock: HTTPXMock,
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
    url = (
        f"{joint_fixture.config.central_api_url}/storages/{joint_fixture.config.storage_alias}"
        + "/uploads/can_remove"
    )
    httpx_mock.add_response(
        status_code=200,
        json=removable_files,
        url=url,
        method="POST",
    )

    # Run the scan and clean operation
    with caplog.at_level("INFO"):
        await joint_fixture.s3_cleaner.scan_and_clean()

    # Check that only the removable_files were deleted from the bucket
    remaining_files = await joint_fixture.s3.storage.list_all_object_ids(interrogation)
    assert set(remaining_files) == set(file_ids) - set(removable_files)

    # Verify log messages based on test case
    if removable_files == file_ids:  # "All" test case
        assert "Starting interrogation bucket cleanup scan." in caplog.text
        assert "Central API indicates 3 file(s) can be removed." in caplog.text
        assert (
            "Cleanup complete: 3 file(s) deleted successfully, 0 failed." in caplog.text
        )
    elif not removable_files:  # "None" test case
        assert "No files marked for removal, exiting." in caplog.text


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_no_files_in_interrogation_bucket(
    joint_fixture: JointFixture,
    httpx_mock: HTTPXMock,
    caplog,
):
    """Test that the cleaner handles an empty interrogation bucket gracefully."""
    # Don't pre-populate any objects in the interrogation bucket
    interrogation = joint_fixture.config.interrogation_bucket_id
    await joint_fixture.s3.storage.create_bucket(interrogation)

    # Verify the bucket is empty
    assert await joint_fixture.s3.storage.list_all_object_ids(interrogation) == []

    # Verify that the Central API isn't called (should quit)
    url = (
        f"{joint_fixture.config.central_api_url}/storages/"
        + f"{joint_fixture.config.storage_alias}/uploads/can_remove"
    )

    def callback(request: httpx.Request) -> httpx.Response:
        raise RuntimeError("Was not supposed to call Central API!")

    httpx_mock.add_callback(callback, url=url)

    # Run the scan and clean operation - should complete without errors
    with caplog.at_level("INFO"):
        await joint_fixture.s3_cleaner.scan_and_clean()

    # Verify the cleaner logged that no files needed cleanup
    assert "No files to clean up, exiting." in caplog.text


@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_central_api_unreachable(
    joint_fixture: JointFixture,
    httpx_mock: HTTPXMock,
    caplog,
):
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

    # The cleaner should raise an exception when unable to reach the API
    with caplog.at_level("ERROR"), pytest.raises(httpx.TimeoutException):
        await joint_fixture.s3_cleaner.scan_and_clean()

    # Verify the error was logged
    assert "Failed to fetch removable files from Central API" in caplog.text

    # Verify that no files were deleted (operation failed before deletion)
    remaining_files = await joint_fixture.s3.storage.list_all_object_ids(interrogation)
    assert set(remaining_files) == set(file_ids)
