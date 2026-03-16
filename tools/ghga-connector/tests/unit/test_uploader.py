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

"""Unit tests for the Uploader class"""

import asyncio
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import AsyncMock, MagicMock

import pytest

from ghga_connector import exceptions
from ghga_connector.core.crypt.checksums import Checksums
from ghga_connector.core.crypt.encryption import FileProcessor
from ghga_connector.core.uploading.uploader import Uploader
from tests.fixtures.utils import TEST_FILE_ID, make_file_info_for_upload

pytestmark = pytest.mark.asyncio

FILE_ID = TEST_FILE_ID
FILE_ALIAS = "test-file"


def make_dummy_file_processor(part_count: int) -> FileProcessor:
    """Create a FileProcessor with fixed data for the given part count"""
    for i in range(part_count):
        yield (i + 1, b"somebytes")


def make_mock_encryptor(parts: list[tuple[int, bytes]] | None = None) -> MagicMock:
    """Create a mock encryptor with pre-populated checksums and an optional part iterator."""
    encryptor = MagicMock()
    encryptor.checksums = Checksums()
    if parts is not None:
        for _, content in parts:
            encryptor.checksums.update_encrypted(content)
        encryptor.process_file.return_value = iter(parts)
    return encryptor


def make_uploader(
    path: Path,
    upload_client: AsyncMock | None = None,
    max_concurrent_uploads: int = 3,
) -> Uploader:
    """Create an Uploader instance wired up with mock dependencies for unit testing."""
    if upload_client is None:
        upload_client = AsyncMock()
    encryptor = make_mock_encryptor()
    file_info = make_file_info_for_upload(
        path=path, alias=FILE_ALIAS, decrypted_size=1000
    )
    return Uploader(
        upload_client=upload_client,
        encryptor=encryptor,
        file_info=file_info,
        max_concurrent_uploads=max_concurrent_uploads,
    )


async def test_initiate_file_upload_returns_file_id():
    """Make sure initiate_file_upload returns the file ID provided by the upload client."""
    with NamedTemporaryFile() as f:
        upload_client = AsyncMock()
        upload_client.create_file_upload.return_value = FILE_ID
        uploader = make_uploader(Path(f.name), upload_client=upload_client)
        file_info = uploader._file_info

        result = await uploader.initiate_file_upload()

        assert result == FILE_ID
        upload_client.create_file_upload.assert_called_once_with(
            file_alias=FILE_ALIAS,
            decrypted_size=file_info.decrypted_size,
            encrypted_size=file_info.encrypted_size,
            part_size=file_info.part_size,
        )


async def test_initiate_file_upload_wraps_exception():
    """Make sure initiate_file_upload() wraps client exceptions as CreateFileUploadError."""
    with NamedTemporaryFile() as f:
        upload_client = AsyncMock()
        upload_client.create_file_upload.side_effect = RuntimeError("network error")
        uploader = make_uploader(Path(f.name), upload_client=upload_client)

        with pytest.raises(exceptions.CreateFileUploadError):
            await uploader.initiate_file_upload()


async def test_delete_file_delegates_to_client():
    """Make sure delete_file() calls UploadClient.delete_file()."""
    with NamedTemporaryFile() as f:
        upload_client = AsyncMock()
        uploader = make_uploader(Path(f.name), upload_client=upload_client)
        uploader._file_id = FILE_ID

        await uploader.delete_file()

        # Verify that delete_file() was called with the right args
        upload_client.delete_file.assert_called_once_with(
            file_id=FILE_ID, file_alias=FILE_ALIAS
        )


async def test_delete_file_wraps_exception():
    """Make sure delete_file() wraps client exceptions as DeleteFileUploadError."""
    with NamedTemporaryFile() as f:
        upload_client = AsyncMock()
        upload_client.delete_file.side_effect = RuntimeError("not found")
        uploader = make_uploader(Path(f.name), upload_client=upload_client)
        uploader._file_id = FILE_ID

        with pytest.raises(exceptions.DeleteFileUploadError):
            await uploader.delete_file()


async def test_upload_file_part_wraps_generic_exception():
    """Make sure _upload_file_part wraps any non-CancelledError exception as UploadFileError."""
    with NamedTemporaryFile() as f:
        upload_client = AsyncMock()
        upload_client.upload_file_part.side_effect = RuntimeError("S3 error")
        uploader = make_uploader(Path(f.name), upload_client=upload_client)
        uploader._file_id = FILE_ID
        uploader._progress_bar = MagicMock()
        uploader._in_sequence_part_number = 1
        file_processor = make_dummy_file_processor(part_count=1)
        with pytest.raises(exceptions.UploadFileError):
            await uploader._upload_file_part(file_processor)


async def test_upload_file_part_reraises_cancelled_error():
    """Make sure _upload_file_part re-raises CancelledError without wrapping it as UploadFileError."""
    with NamedTemporaryFile() as f:
        upload_client = AsyncMock()
        upload_client.upload_file_part.side_effect = asyncio.CancelledError()
        uploader = make_uploader(Path(f.name), upload_client=upload_client)
        uploader._file_id = FILE_ID
        uploader._progress_bar = MagicMock()
        uploader._in_sequence_part_number = 1
        file_processor = make_dummy_file_processor(part_count=1)
        with pytest.raises(asyncio.CancelledError):
            await uploader._upload_file_part(file_processor)


async def test_upload_file_calls_complete_after_all_parts():
    """Make sure upload_file calls complete_file_upload after successfully uploading all parts."""
    with NamedTemporaryFile() as f:
        f.write(b"x" * 100)
        f.flush()

        upload_client = AsyncMock()
        encryptor = make_mock_encryptor(parts=[(1, b"encrypted")])
        mock_file_info = make_file_info_for_upload(path=Path(f.name), alias=FILE_ALIAS)

        uploader = Uploader(
            upload_client=upload_client,
            encryptor=encryptor,
            file_info=mock_file_info,
            max_concurrent_uploads=1,
        )
        uploader._file_id = FILE_ID
        uploader.new_progress_bar = MagicMock(return_value=MagicMock())  # type: ignore

        await uploader.upload_file()

        upload_client.complete_file_upload.assert_called_once()


async def test_upload_file_complete_error_raises_complete_file_upload_error():
    """Test the upload_file method to make sure any errors occurring in the
    complete_file_upload() call are re-raised as CompleteFileUploadError.
    """
    with NamedTemporaryFile() as f:
        f.write(b"x" * 100)
        f.flush()

        upload_client = AsyncMock()
        upload_client.complete_file_upload.side_effect = RuntimeError("server error")
        encryptor = make_mock_encryptor(parts=[(1, b"encrypted")])
        mock_file_info = make_file_info_for_upload(path=Path(f.name), alias=FILE_ALIAS)

        uploader = Uploader(
            upload_client=upload_client,
            encryptor=encryptor,
            file_info=mock_file_info,
            max_concurrent_uploads=1,
        )
        uploader._file_id = FILE_ID
        uploader.new_progress_bar = MagicMock(return_value=MagicMock())  # type: ignore

        with pytest.raises(exceptions.CompleteFileUploadError):
            await uploader.upload_file()


async def test_semaphore_initialized_with_max_concurrent_uploads():
    """Make sure the asyncio Semaphore is created with the given max_concurrent_uploads value."""
    with NamedTemporaryFile() as f:
        max_concurrent = 2
        uploader = make_uploader(Path(f.name), max_concurrent_uploads=max_concurrent)
        assert uploader._semaphore._value == max_concurrent
