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
#

"""Tests for the up- and download functions of the cli"""

import base64
import os
import pathlib
from contextlib import nullcontext
from filecmp import cmp
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import crypt4gh.keys
import httpx
import pytest
from ghga_service_commons.utils.temp_files import big_temp_file
from pytest_httpx import HTTPXMock, httpx_mock  # noqa: F401

from ghga_connector.cli import (
    async_download,
    init_message_display,
    retrieve_upload_parameters,
)
from ghga_connector.constants import DEFAULT_PART_SIZE
from ghga_connector.core import exceptions
from ghga_connector.core.client import async_client
from ghga_connector.core.crypt import Crypt4GHEncryptor
from ghga_connector.core.main import upload_file
from tests.fixtures import state
from tests.fixtures.config import get_test_config
from tests.fixtures.mock_api.app import (
    mock_external_app,
    mock_external_calls,  # noqa: F401
    url_expires_after,
)
from tests.fixtures.s3 import (  # noqa: F401
    S3Fixture,
    get_big_s3_object,
    reset_state,
    s3_fixture,
)
from tests.fixtures.utils import PRIVATE_KEY_FILE, PUBLIC_KEY_FILE, mock_wps_token

GET_PACKAGE_FILES_ATTR = (
    "ghga_connector.core.work_package.WorkPackageAccessor.get_package_files"
)
ENVIRON_DEFAULTS = {
    "DEFAULT_PART_SIZE": str(16 * 1024 * 1024),
    "S3_DOWNLOAD_URL": "test://download.url",
    "S3_UPLOAD_URL_1": "test://upload.url",
    "S3_UPLOAD_URL_2": "test://upload.url",
    "S3_DOWNLOAD_FIELD_SIZE": str(146),
    "FAKE_ENVELOPE": "Fake_envelope",
}
FAKE_ENVELOPE = "Thisisafakeenvelope"
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
def set_env_vars(monkeypatch):
    """Set environment variables"""
    for name, value in ENVIRON_DEFAULTS.items():
        monkeypatch.setenv(name, value)


@pytest.fixture(scope="function", autouse=True)
def apply_test_config():
    """Apply default test config"""
    with patch("ghga_connector.cli.CONFIG", get_test_config()):
        yield


@pytest.fixture(scope="function")
def apply_common_download_mocks(monkeypatch):
    """Monkeypatch download-specific functions and values"""
    monkeypatch.setattr("ghga_connector.cli.get_wps_token", mock_wps_token)
    monkeypatch.setattr(
        "ghga_connector.core.work_package._decrypt",
        lambda data, key: data,
    )
    monkeypatch.setenv("FAKE_ENVELOPE", FAKE_ENVELOPE)


def set_presigned_url_update_endpoint(
    monkeypatch,
    s3_fixture: S3Fixture,  # noqa: F811
    *,
    bucket_id: str,
    object_id: str,
    expires_after: int,
):
    """Temporarily assign the S3 download URL update endpoint in the mock app.

    Since creating the URL requires access to the S3 fixture, this behavior is
    defined here instead of with the rest of the mock api.
    """

    async def update_presigned_url_actual():
        """Create a new presigned download URL for S3."""
        download_url = await s3_fixture.storage.get_object_download_url(
            bucket_id=bucket_id,
            object_id=object_id,
            expires_after=expires_after,
        )

        monkeypatch.setenv("S3_DOWNLOAD_URL", download_url)

    # Monkeypatch the placeholder endpoint function with the above
    monkeypatch.setattr(
        "tests.fixtures.mock_api.app.update_presigned_url_placeholder",
        update_presigned_url_actual,
    )

    # Override the app dependency so it uses the new cache lifespan
    mock_external_app.dependency_overrides[url_expires_after] = lambda: expires_after


@pytest.mark.parametrize(
    "file_size, part_size",
    [
        # first test with some very small files size
        (8, 1024),
        (32, 1024),
        (128, 1024),
        (512, 1024),
        (1024, 1024),
        (2048, 1024),
        (20 * 1024, 1024),
        # then test with larger files sizes
        (6 * 1024 * 1024, 5 * 1024 * 1024),
        (12 * 1024 * 1024, 5 * 1024 * 1024),
        (20 * 1024 * 1024, 1 * 1024 * 1024),
        (20 * 1024 * 1024, 32 * 1024),
        (1 * 1024 * 1024, DEFAULT_PART_SIZE),
        (75 * 1024 * 1024, 10 * 1024 * 1024),
    ],
)
async def test_multipart_download(
    file_size: int,
    part_size: int,
    httpx_mock: HTTPXMock,  # noqa: F811
    s3_fixture: S3Fixture,  # noqa F811
    tmp_path: pathlib.Path,
    monkeypatch,
    mock_external_calls,  # noqa: F811
    apply_common_download_mocks,
):
    """Test the multipart download of a file"""
    # override the default config fixture with updated part size
    monkeypatch.setattr(
        "ghga_connector.cli.CONFIG", get_test_config(part_size=part_size)
    )

    big_object = await get_big_s3_object(s3_fixture, object_size=file_size)

    # The intercepted health check API calls will return the following mock response
    httpx_mock.add_response(json={"status": "OK"})

    # Patch get_package_files
    monkeypatch.setattr(
        GET_PACKAGE_FILES_ATTR,
        AsyncMock(return_value={big_object.object_id: ""}),
    )

    # right now the desired file size is only
    # approximately met by the provided big file:
    actual_file_size = len(big_object.content)
    monkeypatch.setenv("S3_DOWNLOAD_FIELD_SIZE", str(actual_file_size))

    set_presigned_url_update_endpoint(
        monkeypatch,
        s3_fixture,
        bucket_id=big_object.bucket_id,
        object_id=big_object.object_id,
        expires_after=SHORT_LIFESPAN,
    )

    big_file_content = str.encode(FAKE_ENVELOPE)
    big_file_content += big_object.content

    await async_download(
        output_dir=tmp_path,
        my_public_key_path=Path(PUBLIC_KEY_FILE),
        my_private_key_path=Path(PRIVATE_KEY_FILE),
    )

    with open(tmp_path / f"{big_object.object_id}.c4gh", "rb") as file:
        observed_content = file.read()

    assert len(observed_content) == len(big_file_content)
    assert observed_content == big_file_content


@pytest.mark.parametrize(
    "bad_outdir,file_name,expected_exception",
    [
        (False, "file_downloadable", nullcontext()),
        (False, "file_retry", pytest.raises(exceptions.MaxWaitTimeExceededError)),
        (
            True,
            "file_downloadable",
            pytest.raises(exceptions.DirectoryDoesNotExistError),
        ),
        (False, "file_envelope_missing", pytest.raises(exceptions.GetEnvelopeError)),
    ],
)
async def test_download(
    bad_outdir: bool,
    file_name: str,
    expected_exception: Any,
    httpx_mock: HTTPXMock,  # noqa: F811
    s3_fixture: S3Fixture,  # noqa: F811
    tmp_path: pathlib.Path,
    monkeypatch,
    mock_external_calls,  # noqa: F811
    apply_common_download_mocks,
):
    """Test the download of a file"""
    output_dir = Path("/non/existing/path") if bad_outdir else tmp_path

    # Patch get_package_files
    file = state.FILES[file_name]
    monkeypatch.setattr(
        GET_PACKAGE_FILES_ATTR,
        AsyncMock(return_value={file.file_id: ""}),
    )

    if file.populate_storage:
        set_presigned_url_update_endpoint(
            monkeypatch,
            s3_fixture,
            bucket_id=file.grouping_label,
            object_id=file.file_id,
            expires_after=SHORT_LIFESPAN,
        )
    else:
        monkeypatch.setenv("S3_DOWNLOAD_URL", "")

    monkeypatch.setenv("S3_DOWNLOAD_FIELD_SIZE", str(os.path.getsize(file.file_path)))

    # The intercepted health check API calls will return the following mock response
    httpx_mock.add_response(json={"status": "OK"})

    with expected_exception:
        await async_download(
            output_dir=output_dir,
            my_public_key_path=Path(PUBLIC_KEY_FILE),
            my_private_key_path=Path(PRIVATE_KEY_FILE),
        )

    tmp_file = tmp_path / "file_with_envelope"

    # Copy fake envelope into new temp file, then append the test file
    with tmp_file.open("wb") as file_write:
        with file.file_path.open("rb") as file_read:
            buffer = file_read.read()
            file_write.write(str.encode(FAKE_ENVELOPE))
            file_write.write(buffer)

    if not expected_exception:
        assert cmp(output_dir / f"{file.file_id}.c4gh", tmp_file)


async def test_file_not_downloadable(
    httpx_mock: HTTPXMock,  # noqa: F811
    s3_fixture: S3Fixture,  # noqa: F811
    tmp_path: pathlib.Path,
    monkeypatch,
    mock_external_calls,  # noqa: F811
    apply_common_download_mocks,
):
    """Test to try downloading a file that isn't in storage.

    Tests for 403 error behavior as well as the case where an expected file ID is
    reported missing by the download controller API (and the user chooses not to
    continue the download).
    """
    output_dir = tmp_path

    # The intercepted health check API calls will return the following mock response
    httpx_mock.add_response(json={"status": "OK"})

    # Patch get_package_files
    file = state.FILES["file_not_downloadable"]
    monkeypatch.setattr(
        GET_PACKAGE_FILES_ATTR,
        AsyncMock(return_value={file.file_id: ""}),
    )

    monkeypatch.setenv("S3_DOWNLOAD_FIELD_SIZE", str(os.path.getsize(file.file_path)))

    # 403 caused by an invalid auth token
    with (
        patch(
            "ghga_connector.core.work_package._decrypt",
            lambda data, key: "authfail_normal",
        ),
        pytest.raises(
            exceptions.UnauthorizedAPICallError,
            match=r"This is not the token you're looking for\.",
        ),
    ):
        await async_download(
            output_dir=output_dir,
            my_public_key_path=Path(PUBLIC_KEY_FILE),
            my_private_key_path=Path(PRIVATE_KEY_FILE),
        )

    # 403 caused by requesting file ID that's not part of the work order token
    with (
        patch(
            "ghga_connector.core.work_package._decrypt",
            lambda data, key: "file_id_mismatch",
        ),
        pytest.raises(
            exceptions.UnauthorizedAPICallError,
            match="Endpoint file ID did not match file ID"
            " announced in work order token",
        ),
    ):
        await async_download(
            output_dir=output_dir,
            my_public_key_path=Path(PUBLIC_KEY_FILE),
            my_private_key_path=Path(PRIVATE_KEY_FILE),
        )

    # Exception arising when the file ID is valid, but not found in the DCS (and the
    #  user inputs 'no' instead of 'yes' when prompted if they want to continue anyway)
    with (
        patch(
            "ghga_connector.core.downloading.batch_processing.CliIoHandler.get_input",
            return_value="no",
        ),
        pytest.raises(exceptions.AbortBatchProcessError),
    ):
        await async_download(
            output_dir=output_dir,
            my_public_key_path=Path(PUBLIC_KEY_FILE),
            my_private_key_path=Path(PRIVATE_KEY_FILE),
        )


@pytest.mark.parametrize(
    "file_name,expected_exception",
    [
        ("file_uploadable", nullcontext()),
        ("file_not_uploadable", pytest.raises(exceptions.StartUploadError)),
        ("file_with_bad_path", pytest.raises(exceptions.FileDoesNotExistError)),
        ("encrypted_file", pytest.raises(exceptions.FileAlreadyEncryptedError)),
    ],
)
async def test_upload(
    file_name: str,
    expected_exception: Any,
    httpx_mock: HTTPXMock,  # noqa: F811
    s3_fixture: S3Fixture,  # noqa F811
    monkeypatch,
    mock_external_calls,  # noqa: F811
    tmpdir,
):
    """Test the upload of a file, expects Abort, if the file was not found"""
    uploadable_file = state.FILES[file_name]

    # The intercepted health check API calls will return the following mock response
    httpx_mock.add_response(json={"status": "OK"})

    if file_name == "encrypted_file":
        # encrypt test file on the fly
        server_pubkey = base64.b64encode(
            crypt4gh.keys.get_public_key(PUBLIC_KEY_FILE)
        ).decode("utf-8")
        encryptor = Crypt4GHEncryptor(
            part_size=8 * 1024**3,
            server_public_key=server_pubkey,
            private_key_path=PRIVATE_KEY_FILE,
            passphrase=None,
        )
        with uploadable_file.file_path.open("rb") as source_file:
            with open(tmpdir.join("encrypted_file"), "wb") as encrypted_file:
                for chunk in encryptor.process_file(file=source_file):
                    encrypted_file.write(chunk)
        file_path = Path(encrypted_file.name)
    else:
        file_path = uploadable_file.file_path

    file_path = file_path.resolve()

    # initiate upload
    upload_id = await s3_fixture.storage.init_multipart_upload(
        bucket_id=uploadable_file.grouping_label,
        object_id=uploadable_file.file_id,
    )

    upload_url = await s3_fixture.storage.get_part_upload_url(
        bucket_id=uploadable_file.grouping_label,
        object_id=uploadable_file.file_id,
        upload_id=upload_id,
        part_number=1,
    )

    monkeypatch.setenv("S3_UPLOAD_URL_1", upload_url)

    with expected_exception:
        message_display = init_message_display(debug=True)
        async with async_client() as client:
            parameters = await retrieve_upload_parameters(client=client)
            await upload_file(
                api_url=parameters.ucs_api_url,
                client=client,
                file_id=uploadable_file.file_id,
                file_path=file_path,
                message_display=message_display,
                server_public_key=parameters.server_pubkey,
                my_public_key_path=Path(PUBLIC_KEY_FILE),
                my_private_key_path=Path(PRIVATE_KEY_FILE),
                part_size=DEFAULT_PART_SIZE,
            )

        await s3_fixture.storage.complete_multipart_upload(
            upload_id=upload_id,
            bucket_id=uploadable_file.grouping_label,
            object_id=uploadable_file.file_id,
        )

        assert await s3_fixture.storage.does_object_exist(
            bucket_id=uploadable_file.grouping_label,
            object_id=uploadable_file.file_id,
        )


@pytest.mark.parametrize(
    "file_size,anticipated_part_size",
    [
        (6 * 1024 * 1024, 8),
        (20 * 1024 * 1024, 16),
    ],
)
async def test_multipart_upload(
    file_size: int,
    anticipated_part_size: int,
    httpx_mock: HTTPXMock,  # noqa: F811
    s3_fixture: S3Fixture,  # noqa F811
    monkeypatch,
    mock_external_calls,  # noqa: F811
):
    """Test the upload of a file, expects Abort, if the file was not found"""
    bucket_id = s3_fixture.existing_buckets[0]
    file_id = "uploadable-" + str(anticipated_part_size)

    # The intercepted health check API calls will return the following mock response
    httpx_mock.add_response(json={"status": "OK"})

    anticipated_part_size = anticipated_part_size * 1024 * 1024

    anticipated_part_quantity = file_size // anticipated_part_size

    if anticipated_part_quantity * anticipated_part_size < file_size:
        anticipated_part_quantity += 1

    # initiate upload
    upload_id = await s3_fixture.storage.init_multipart_upload(
        bucket_id=bucket_id,
        object_id=file_id,
    )

    # create presigned url for upload part 1
    upload_url_1 = await s3_fixture.storage.get_part_upload_url(
        upload_id=upload_id,
        bucket_id=bucket_id,
        object_id=file_id,
        part_number=1,
    )

    # create presigned url for upload part 2
    upload_url_2 = await s3_fixture.storage.get_part_upload_url(
        upload_id=upload_id,
        bucket_id=bucket_id,
        object_id=file_id,
        part_number=2,
    )

    monkeypatch.setenv("S3_UPLOAD_URL_1", upload_url_1)
    monkeypatch.setenv("S3_UPLOAD_URL_2", upload_url_2)

    # create big temp file
    with big_temp_file(file_size) as file:
        message_display = init_message_display(debug=True)
        async with async_client() as client:
            parameters = await retrieve_upload_parameters(client=client)
            await upload_file(
                api_url=parameters.ucs_api_url,
                client=client,
                file_id=file_id,
                file_path=Path(file.name),
                message_display=message_display,
                server_public_key=parameters.server_pubkey,
                my_public_key_path=Path(PUBLIC_KEY_FILE),
                my_private_key_path=Path(PRIVATE_KEY_FILE),
                part_size=DEFAULT_PART_SIZE,
            )

    # confirm upload
    await s3_fixture.storage.complete_multipart_upload(
        upload_id=upload_id,
        bucket_id=bucket_id,
        object_id=file_id,
        anticipated_part_quantity=anticipated_part_quantity,
        anticipated_part_size=anticipated_part_size,
    )
    assert await s3_fixture.storage.does_object_exist(
        bucket_id=bucket_id,
        object_id=file_id,
    )


async def test_upload_bad_url(httpx_mock: HTTPXMock, mock_external_calls):  # noqa: F811
    """Check that the right error is raised for a bad URL in the upload logic."""
    # The intercepted health check API call will return the following mock response
    httpx_mock.add_exception(httpx.RequestError(""))

    uploadable_file = state.FILES["file_uploadable"]
    file_path = uploadable_file.file_path.resolve()

    with pytest.raises(exceptions.ApiNotReachableError):
        message_display = init_message_display(debug=True)
        async with async_client() as client:
            parameters = await retrieve_upload_parameters(client=client)
            await upload_file(
                api_url=parameters.ucs_api_url,
                client=client,
                file_id=uploadable_file.file_id,
                file_path=file_path,
                message_display=message_display,
                server_public_key=parameters.server_pubkey,
                my_public_key_path=Path(PUBLIC_KEY_FILE),
                my_private_key_path=Path(PRIVATE_KEY_FILE),
                part_size=DEFAULT_PART_SIZE,
            )


async def test_download_bad_url(
    httpx_mock: HTTPXMock,  # noqa: F811
    tmp_path: pathlib.Path,
    monkeypatch,
    mock_external_calls,  # noqa: F811
    apply_common_download_mocks,
):
    """Check that the right error is raised for a bad URL in the download logic."""
    httpx_mock.add_exception(httpx.RequestError(""))

    # Patch get_package_files
    file = state.FILES["file_downloadable"]
    monkeypatch.setattr(
        GET_PACKAGE_FILES_ATTR,
        AsyncMock(return_value={file.file_id: ""}),
    )

    with pytest.raises(exceptions.ApiNotReachableError):
        await async_download(
            output_dir=tmp_path,
            my_public_key_path=Path(PUBLIC_KEY_FILE),
            my_private_key_path=Path(PRIVATE_KEY_FILE),
        )
