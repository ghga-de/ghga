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
#

"""Tests for the up- and download functions of the cli"""

import os
import pathlib
from contextlib import nullcontext
from filecmp import cmp
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from ghga_connector import exceptions
from ghga_connector.constants import C4GH, DEFAULT_PART_SIZE
from ghga_connector.core.main import async_download
from tests.fixtures import state
from tests.fixtures.config import get_test_config
from tests.fixtures.mock_api.apis import (
    WORK_ORDER_TOKEN,
    MockApis,
    StagedObject,
    mock_apis,  # noqa: F401
)
from tests.fixtures.mock_api.router import (
    httpyexpect_error,
    mock_health_checks,
    respond,
)
from tests.fixtures.s3 import (  # noqa: F401
    S3Fixture,
    get_big_s3_object,
    reset_state,
    s3_fixture,
)
from tests.fixtures.utils import (
    PRIVATE_KEY_FILE,
    PUBLIC_KEY_FILE,
    patch_work_package_functions,  # noqa: F401
)

GET_PACKAGE_FILES_ATTR = (
    "ghga_connector.core.work_package.WorkPackageClient.get_package_files"
)
FAKE_ENVELOPE = b"Thisisafakeenvelope"

pytestmark = [pytest.mark.asyncio(loop_scope="session")]


@pytest.fixture(scope="function", autouse=True)
def apply_test_config():
    """Apply default test config"""
    with patch("ghga_connector.config.CONFIG", get_test_config()):
        yield


def stage(
    s3_fixture: S3Fixture,  # noqa: F811
    *,
    file_id: str,
    bucket_id: str,
    size: int,
    envelope: bytes | None = FAKE_ENVELOPE,
) -> StagedObject:
    """Describe an S3 object as staged, presigning its URL fresh on every request."""

    def presign(expires_after: int):
        """Presign a download URL for the object."""
        return s3_fixture.storage.get_object_download_url(
            bucket_id=bucket_id, object_id=file_id, expires_after=expires_after
        )

    return StagedObject(
        file_id=file_id, size=size, presign_download_url=presign, envelope=envelope
    )


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
        (1 * 1024 * 1024, DEFAULT_PART_SIZE),
        (75 * 1024 * 1024, 10 * 1024 * 1024),
    ],
)
async def test_multipart_download(
    file_size: int,
    part_size: int,
    s3_fixture: S3Fixture,  # noqa F811
    tmp_path: pathlib.Path,
    monkeypatch,
    mock_apis: MockApis,  # noqa: F811
    patch_work_package_functions,  # noqa: F811
):
    """Test the multipart download of a file"""
    # override the default config fixture with updated part size
    monkeypatch.setattr(
        "ghga_connector.config.CONFIG", get_test_config(part_size=part_size)
    )

    big_object = await get_big_s3_object(s3_fixture, object_size=file_size)

    mock_health_checks(monkeypatch)

    # Patch get_package_files
    monkeypatch.setattr(
        GET_PACKAGE_FILES_ATTR,
        AsyncMock(return_value={big_object.object_id: ""}),
    )

    # right now the desired file size is only
    # approximately met by the provided big file:
    actual_file_size = len(big_object.content)

    mock_apis.download.staged = stage(
        s3_fixture,
        file_id=big_object.object_id,
        bucket_id=big_object.bucket_id,
        size=actual_file_size,
    )

    big_file_content = FAKE_ENVELOPE + big_object.content

    await async_download(
        output_dir=tmp_path,
        my_public_key_path=Path(PUBLIC_KEY_FILE),
        my_private_key_path=Path(PRIVATE_KEY_FILE),
    )

    with open(tmp_path / f"{big_object.object_id}{C4GH}", "rb") as file:
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
    s3_fixture: S3Fixture,  # noqa: F811
    tmp_path: pathlib.Path,
    monkeypatch,
    mock_apis: MockApis,  # noqa: F811
    patch_work_package_functions,  # noqa: F811
):
    """Test the download of a file"""
    output_dir = Path("/non/existing/path") if bad_outdir else tmp_path

    # Patch get_package_files
    file = state.FILES[file_name]
    monkeypatch.setattr(
        GET_PACKAGE_FILES_ATTR,
        AsyncMock(return_value={file.file_id: ""}),
    )

    # The envelope is only served for files that have one - "file_envelope_missing"
    # doesn't.
    if file.populate_storage:
        mock_apis.download.staged = stage(
            s3_fixture,
            file_id=file.file_id,
            bucket_id=file.grouping_label,
            size=os.path.getsize(file.file_path),
            envelope=None if file_name == "file_envelope_missing" else FAKE_ENVELOPE,
        )

    # "file_retry" is never staged - the API keeps reporting it as still being staged
    # until the connector gives up waiting.
    if file_name == "file_retry":
        mock_apis.download.on_get_drs_object = respond(
            202, headers={"Retry-After": "10"}
        )

    mock_health_checks(monkeypatch)

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
            file_write.write(FAKE_ENVELOPE)
            file_write.write(buffer)

    if not expected_exception:
        assert cmp(output_dir / f"{file.file_id}{C4GH}", tmp_file)


async def test_file_not_downloadable(
    s3_fixture: S3Fixture,  # noqa: F811
    tmp_path: pathlib.Path,
    monkeypatch,
    mock_apis: MockApis,  # noqa: F811
    patch_work_package_functions,  # noqa: F811
):
    """Test to try downloading a file that isn't in storage.

    Tests for 403 error behavior as well as the case where an expected file ID is
    reported missing by the download controller API (and the user chooses not to
    continue the download).
    """
    output_dir = tmp_path

    mock_health_checks(monkeypatch)

    # Patch get_package_files
    file = state.FILES["file_not_downloadable"]
    monkeypatch.setattr(
        GET_PACKAGE_FILES_ATTR,
        AsyncMock(return_value={file.file_id: ""}),
    )

    # Nothing is staged, so the Download API reports the file as unknown
    describe_drs_object = mock_apis.download.on_get_drs_object

    # 403 caused by an invalid auth token. A plain 403 explains itself in `detail`, an
    # httpyexpect one in `description`, and the connector reads whichever is there - so
    # the two refusals below exercise both flavors.
    mock_apis.download.on_get_drs_object = respond(
        403, json={"detail": "This is not the token you're looking for."}
    )
    with pytest.raises(
        exceptions.UnauthorizedAPICallError,
        match=r"This is not the token you're looking for\.",
    ):
        await async_download(
            output_dir=output_dir,
            my_public_key_path=Path(PUBLIC_KEY_FILE),
            my_private_key_path=Path(PRIVATE_KEY_FILE),
        )

    # The work order token the connector fetched has to have reached the Download API as
    # the bearer token - `patch_work_package_functions` leaves `_decrypt` as the identity.
    assert (
        mock_apis.download.last_request.headers["authorization"]
        == f"Bearer {WORK_ORDER_TOKEN}"
    )

    # 403 caused by requesting file ID that's not part of the work order token
    mock_apis.download.on_get_drs_object = lambda request, **path_variables: (
        httpyexpect_error(
            403,
            "wrongFileAuthorizationError",
            "Endpoint file ID did not match file ID announced in work order token.",
            {},
        )
    )
    with pytest.raises(
        exceptions.UnauthorizedAPICallError,
        match="Endpoint file ID did not match file ID announced in work order token",
    ):
        await async_download(
            output_dir=output_dir,
            my_public_key_path=Path(PUBLIC_KEY_FILE),
            my_private_key_path=Path(PRIVATE_KEY_FILE),
        )

    # Restore the default handler for the "file is unknown" case below
    mock_apis.download.on_get_drs_object = describe_drs_object

    # Exception arising when the file ID is valid, but not found in the Download API (and the
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


async def test_download_bad_url(
    tmp_path: pathlib.Path,
    monkeypatch,
    mock_apis: MockApis,  # noqa: F811
    patch_work_package_functions,  # noqa: F811
):
    """Check that the right error is raised for a bad URL in the download logic."""
    mock_health_checks(monkeypatch, reachable=False)

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
