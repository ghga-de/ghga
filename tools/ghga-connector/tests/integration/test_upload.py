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

"""Integration tests for the upload path"""

from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import httpx
import pytest
from ghga_service_commons.utils.temp_files import big_temp_file
from pytest_httpx import HTTPXMock

from ghga_connector import exceptions
from ghga_connector.config import set_runtime_config
from ghga_connector.core.client import async_client
from ghga_connector.core.main import upload_files
from ghga_connector.core.uploading.structs import FileInfoForUpload
from ghga_connector.core.utils import modify_for_debug
from tests.fixtures.config import get_test_config
from tests.fixtures.mock_api.app import mock_external_calls  # noqa: F401
from tests.fixtures.s3 import S3Fixture, s3_fixture  # noqa: F401
from tests.fixtures.utils import (
    PRIVATE_KEY_FILE,
    PUBLIC_KEY_FILE,
    patch_work_package_functions,  # noqa: F401
)

ALIAS = "test-file-1"
SIZE = 10 * 1024 * 1024
FILE_ID = UUID("550e8400-e29b-41d4-a716-446655440002")
SHORT_LIFESPAN = 10
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.httpx_mock(
        assert_all_responses_were_requested=False,
        assert_all_requests_were_expected=False,
        can_send_already_matched_responses=True,
        should_mock=lambda request: str(request.url).endswith("/health"),
    ),
]


@pytest.fixture(scope="function", autouse=True)
def apply_test_config():
    """Apply default test config"""
    with patch("ghga_connector.config.CONFIG", get_test_config()):
        yield


def set_presigned_upload_url_update_endpoint(
    monkeypatch,
    s3_fixture: S3Fixture,  # noqa: F811
    *,
    bucket_id: str,
    upload_id_ref: list[str],
):
    """Temporarily assign the S3 upload URL update endpoint in the mock app.

    Since creating the URL requires access to the S3 fixture, this behavior is
    defined here instead of with the rest of the mock api.
    """

    async def update_part_upload_url(object_id: str, part_no: int) -> str:
        """Create a new presigned upload URL for S3."""
        assert upload_id_ref, "No upload ID found"
        upload_url = await s3_fixture.storage.get_part_upload_url(
            bucket_id=bucket_id,
            object_id=object_id,
            upload_id=upload_id_ref[0],
            part_number=part_no,
        )
        return upload_url

    # Monkeypatch the placeholder function with the above
    monkeypatch.setattr(
        "tests.fixtures.mock_api.app.update_part_upload_url_placeholder",
        update_part_upload_url,
    )


def set_init_upload_placeholder(
    monkeypatch,
    s3_fixture: S3Fixture,  # noqa: F811
    *,
    bucket_id: str,
    upload_id_ref: list[str],
):
    """Patch the `init_upload_placeholder` function in the mock app with an actual
    function to initiate a multipart upload in the given S3 fixture and return the
    upload ID.
    """

    async def init_upload(object_id: str):
        """Initiate a multipart upload in the given S3 fixture and pass the upload ID to
        the upload ID ref so it can be accessed by the test function.
        """
        upload_id_ref.clear()
        upload_id_ref.append(
            await s3_fixture.storage.init_multipart_upload(
                bucket_id=bucket_id, object_id=object_id
            )
        )

    async def complete_upload(object_id: str):
        """Complete an S3 upload"""
        assert upload_id_ref, "No upload ID found"
        await s3_fixture.storage.complete_multipart_upload(
            upload_id=upload_id_ref.pop(), bucket_id=bucket_id, object_id=object_id
        )

    # Monkeypatch the placeholder functions with the above
    monkeypatch.setattr(
        "tests.fixtures.mock_api.app.init_upload_placeholder", init_upload
    )
    monkeypatch.setattr(
        "tests.fixtures.mock_api.app.terminate_upload_placeholder", complete_upload
    )


async def test_upload_journey(
    s3_fixture: S3Fixture,  # noqa: F811
    httpx_mock: HTTPXMock,
    mock_external_calls,  # noqa: F811
    monkeypatch,
    patch_work_package_functions,  # noqa: F811
):
    """Test the whole upload path"""
    bucket_id = s3_fixture.existing_buckets[0]
    monkeypatch.setattr(
        "ghga_connector.core.uploading.api_calls.is_service_healthy", lambda s: True
    )

    upload_id_ref: list[str] = []

    set_init_upload_placeholder(
        monkeypatch, s3_fixture, bucket_id=bucket_id, upload_id_ref=upload_id_ref
    )
    set_presigned_upload_url_update_endpoint(
        monkeypatch,
        s3_fixture,
        bucket_id=bucket_id,
        upload_id_ref=upload_id_ref,
    )

    # create 2 big temp files
    with big_temp_file(SIZE) as file:
        file_info = FileInfoForUpload(ALIAS, Path(file.name), SIZE)
        async with async_client() as client, set_runtime_config(client=client):
            await upload_files(
                client=client,
                file_info_list=[file_info],
                my_public_key_path=PUBLIC_KEY_FILE,
                my_private_key_path=PRIVATE_KEY_FILE,
                passphrase=None,
            )


async def test_upload_bad_url(
    httpx_mock: HTTPXMock,
    mock_external_calls,  # noqa: F811
    monkeypatch,
    patch_work_package_functions,  # noqa: F811
):
    """Check that the right error is raised for a bad URL in the upload logic."""
    # The intercepted health check API call will return the following mock response
    httpx_mock.add_exception(httpx.RequestError(""))
    with big_temp_file(SIZE) as file, pytest.raises(exceptions.ApiNotReachableError):
        modify_for_debug(debug=True)
        file_info = FileInfoForUpload(ALIAS, Path(file.name), SIZE)
        async with async_client() as client, set_runtime_config(client=client):
            await upload_files(
                client=client,
                file_info_list=[file_info],
                my_public_key_path=PUBLIC_KEY_FILE,
                my_private_key_path=PRIVATE_KEY_FILE,
                passphrase=None,
            )
