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

"""Unit tests for upload_files_from_list in batch_processing"""

from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import SecretBytes

from ghga_connector import exceptions
from ghga_connector.core.uploading.batch_processing import upload_files_from_list
from tests.fixtures.utils import (
    TEST_FILE_ID,
    TEST_STORAGE_ALIAS1,
    make_file_info_for_upload,
)

pytestmark = pytest.mark.asyncio


def make_mock_uploader(
    *,
    upload_raises: BaseException | None = None,
) -> AsyncMock:
    """Create a mock Uploader with configurable upload_file side effect."""
    uploader = AsyncMock()
    uploader.initiate_file_upload.return_value = TEST_FILE_ID, TEST_STORAGE_ALIAS1
    if upload_raises is not None:
        uploader.upload_file.side_effect = upload_raises
    return uploader


async def test_upload_files_from_list_success_does_not_call_delete():
    """Make sure delete_file is never called when an upload succeeds."""
    with NamedTemporaryFile() as f:
        file_info = make_file_info_for_upload(path=Path(f.name))
        mock_uploader = make_mock_uploader()

        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.Uploader",
                return_value=mock_uploader,
            ),
            patch("ghga_connector.core.uploading.batch_processing.Crypt4GHEncryptor"),
        ):
            await upload_files_from_list(
                upload_client=AsyncMock(),
                file_info_list=[file_info],
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
            )

        mock_uploader.upload_file.assert_called_once()
        mock_uploader.delete_file.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        exceptions.CreateFileUploadError(
            file_alias="test-file", reason="something went wrong"
        ),
        KeyboardInterrupt(),
    ],
)
async def test_upload_files_from_list_deletes_on_errors(error: BaseException):
    """Make sure delete_file() is called when upload_file() raises
    either a KeyboardInterrupt or any other error.
    """
    with NamedTemporaryFile() as f:
        file_info = make_file_info_for_upload(path=Path(f.name))
        mock_uploader = make_mock_uploader(upload_raises=error)

        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.Uploader",
                return_value=mock_uploader,
            ),
            patch("ghga_connector.core.uploading.batch_processing.Crypt4GHEncryptor"),
        ):
            await upload_files_from_list(
                upload_client=AsyncMock(),
                file_info_list=[file_info],
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
            )

        mock_uploader.delete_file.assert_called_once()


async def test_upload_files_from_list_processes_each_file():
    """Make sure each file in the list has initiate_file_upload and upload_file called exactly once."""
    with NamedTemporaryFile() as f1, NamedTemporaryFile() as f2:
        file_infos = [
            make_file_info_for_upload(path=Path(f1.name), alias="file-one"),
            make_file_info_for_upload(path=Path(f2.name), alias="file-two"),
        ]
        mock_uploader_1 = make_mock_uploader()
        mock_uploader_2 = make_mock_uploader()

        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.Uploader",
                side_effect=[mock_uploader_1, mock_uploader_2],
            ),
            patch("ghga_connector.core.uploading.batch_processing.Crypt4GHEncryptor"),
        ):
            await upload_files_from_list(
                upload_client=AsyncMock(),
                file_info_list=file_infos,
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
            )

        for mock_uploader in [mock_uploader_1, mock_uploader_2]:
            mock_uploader.initiate_file_upload.assert_called_once()
            mock_uploader.upload_file.assert_called_once()
