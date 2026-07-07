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
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest

from ghga_connector import exceptions
from ghga_connector.constants import (
    MAX_RETRIES,
    MAX_UPLOAD_BACKOFF_SEC,
    UPLOAD_RETRY_BACKOFF_SEC,
)
from ghga_connector.core.crypt.checksums import Checksums
from ghga_connector.core.crypt.encryption import FileProcessor
from ghga_connector.core.tasks import TaskHandler
from ghga_connector.core.uploading.uploader import Uploader
from tests.fixtures.utils import (
    TEST_FILE_ID,
    TEST_STORAGE_ALIAS2,
    make_file_info_for_upload,
)

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
    file_info = make_file_info_for_upload(
        path=path, alias=FILE_ALIAS, decrypted_size=1000
    )
    return Uploader(
        upload_client=upload_client,
        file_info=file_info,
        max_concurrent_uploads=max_concurrent_uploads,
    )


async def test_new_progress_bar_uses_display_name():
    """The progress bar label uses display_name when given, else the file alias."""
    with NamedTemporaryFile() as f:
        file_info = make_file_info_for_upload(
            path=Path(f.name), alias=FILE_ALIAS, decrypted_size=1000
        )

        # Default: the bar falls back to the file alias.
        default = Uploader(
            upload_client=AsyncMock(), file_info=file_info, max_concurrent_uploads=1
        )
        assert default.new_progress_bar()._file_name == FILE_ALIAS

        # An explicit display_name is used for the bar; the API alias is untouched.
        custom = Uploader(
            upload_client=AsyncMock(),
            file_info=file_info,
            max_concurrent_uploads=1,
            display_name="short … name",
        )
        assert custom.new_progress_bar()._file_name == "short … name"
        assert custom._file_alias == FILE_ALIAS


async def test_initiate_file_upload_returns_file_id():
    """Make sure initiate_file_upload returns the file ID provided by the upload client."""
    with NamedTemporaryFile() as f:
        upload_client = AsyncMock()
        upload_client.create_file_upload.return_value = FILE_ID, TEST_STORAGE_ALIAS2
        uploader = make_uploader(Path(f.name), upload_client=upload_client)
        file_info = uploader._file_info

        result = await uploader.initiate_file_upload()

        assert result == (FILE_ID, TEST_STORAGE_ALIAS2)
        upload_client.create_file_upload.assert_called_once_with(
            file_alias=FILE_ALIAS,
            decrypted_size=file_info.decrypted_size,
            encrypted_size=file_info.encrypted_size,
            part_size=file_info.part_size,
            overwrite=False,
        )


async def test_initiate_file_upload_forwards_overwrite():
    """Test that the Uploader class correctly sets 'overwrite' in call to create_file_upload."""
    with NamedTemporaryFile() as f:
        upload_client = AsyncMock()
        upload_client.create_file_upload.return_value = FILE_ID, TEST_STORAGE_ALIAS2
        file_info = make_file_info_for_upload(
            path=Path(f.name), alias=FILE_ALIAS, decrypted_size=1000
        )
        uploader = Uploader(
            upload_client=upload_client,
            file_info=file_info,
            max_concurrent_uploads=1,
            overwrite=True,
        )

        await uploader.initiate_file_upload()

        assert upload_client.create_file_upload.call_args.kwargs["overwrite"] is True


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


async def test_upload_file_part_wraps_exception_with_blank_message(caplog):
    """Make sure _upload_file_part handles exceptions with empty messages correctly."""
    upload_client = AsyncMock()
    upload_client.upload_file_part.side_effect = httpx.ReadError("")
    file_processor = make_dummy_file_processor(part_count=1)

    with NamedTemporaryFile() as f:
        uploader = make_uploader(Path(f.name), upload_client=upload_client)
        uploader._file_id = FILE_ID
        uploader._progress_bar = MagicMock()
        uploader._in_sequence_part_number = 1

        task_handler = TaskHandler()
        task_handler.schedule(uploader._upload_file_part(file_processor))
        with caplog.at_level(logging.ERROR, logger="asyncio"):
            with pytest.raises(exceptions.UploadFileError):
                await task_handler.gather()
            await asyncio.sleep(0)  # let the finalize done-callback run and log

        assert (
            "an exception of type 'httpx.ReadError' was raised without a message"
            in caplog.text
        )


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
        mock_file_info = make_file_info_for_upload(path=Path(f.name), alias=FILE_ALIAS)

        uploader = Uploader(
            upload_client=upload_client,
            file_info=mock_file_info,
            max_concurrent_uploads=1,
        )
        uploader._file_id = FILE_ID
        uploader.new_progress_bar = MagicMock(return_value=MagicMock())  # type: ignore
        encryptor = make_mock_encryptor(parts=[(1, b"encrypted")])
        await uploader.upload_file(encryptor=encryptor)
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
        mock_file_info = make_file_info_for_upload(path=Path(f.name), alias=FILE_ALIAS)

        uploader = Uploader(
            upload_client=upload_client,
            file_info=mock_file_info,
            max_concurrent_uploads=1,
        )
        uploader._file_id = FILE_ID
        uploader.new_progress_bar = MagicMock(return_value=MagicMock())  # type: ignore

        with pytest.raises(exceptions.CompleteFileUploadError):
            encryptor = make_mock_encryptor(parts=[(1, b"encrypted")])
            await uploader.upload_file(encryptor=encryptor)


async def test_initiate_file_upload_retries_on_429_with_increasing_backoff():
    """Test that initiate_file_upload() can return/finish correctly if the nth attempt
    is successful.
    """
    with NamedTemporaryFile() as f:
        # Use a mock UploadClient that errors on the first two calls but succeeds on #3.
        upload_client = AsyncMock()
        upload_client.create_file_upload.side_effect = [
            exceptions.TooManyRequestsError(),
            exceptions.TooManyRequestsError(),
            (FILE_ID, TEST_STORAGE_ALIAS2),
        ]
        uploader = make_uploader(Path(f.name), upload_client=upload_client)

        # Patch the sleep method so we don't actually wait
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await uploader.initiate_file_upload()

        # The eventual success must be returned unchanged to the caller.
        assert result == (FILE_ID, TEST_STORAGE_ALIAS2)

        # Should have slept twice (two retries)
        assert mock_sleep.await_count == 2

        # Examine/confirm the sleep args were correct
        assert mock_sleep.call_args_list == [
            call(min(UPLOAD_RETRY_BACKOFF_SEC * (2**0), MAX_UPLOAD_BACKOFF_SEC)),
            call(min(UPLOAD_RETRY_BACKOFF_SEC * (2**1), MAX_UPLOAD_BACKOFF_SEC)),
        ]


async def test_initiate_file_upload_raises_after_exhausted_429_retries():
    """When create_file_upload raises TooManyRequestsError, initiate_file_upload
    should sleep MAX_RETRIES times then re-raise the error as CreateFileUploadError
    after retrying MAX_RETRIES times.
    """
    with NamedTemporaryFile() as f:
        # Use a mock UploadClient set to raise TooManyRequestsError
        upload_client = AsyncMock()
        upload_client.create_file_upload.side_effect = exceptions.TooManyRequestsError()
        uploader = make_uploader(Path(f.name), upload_client=upload_client)

        # Patch sleep() so we don't actually wait (and we can check the args later)
        with (
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            pytest.raises(exceptions.CreateFileUploadError) as exc_info,
        ):
            await uploader.initiate_file_upload()

        # Verify that the TooManyRequestsError was raised from the TooManyRequestsErr
        assert isinstance(exc_info.value.__cause__, exceptions.TooManyRequestsError)

        # Verify that we did the correct number of retries
        assert upload_client.create_file_upload.call_count == MAX_RETRIES + 1

        # One sleep per retry
        assert mock_sleep.await_count == MAX_RETRIES

        # Confirm the sleep duration for each retry
        expected_sleep_calls = [
            call(min(UPLOAD_RETRY_BACKOFF_SEC * (2**n), MAX_UPLOAD_BACKOFF_SEC))
            for n in range(MAX_RETRIES)
        ]
        assert mock_sleep.call_args_list == expected_sleep_calls


async def test_semaphore_initialized_with_max_concurrent_uploads():
    """Make sure the asyncio Semaphore is created with the given max_concurrent_uploads value."""
    with NamedTemporaryFile() as f:
        max_concurrent = 2
        uploader = make_uploader(Path(f.name), max_concurrent_uploads=max_concurrent)
        assert uploader._semaphore._value == max_concurrent
