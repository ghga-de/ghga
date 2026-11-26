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

import asyncio
import math
import signal
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import SecretBytes

from ghga_connector import exceptions
from ghga_connector.constants import BATCH_RETRY_BACKOFF_SEC
from ghga_connector.core.crypt.checksums import Checksums
from ghga_connector.core.uploading.batch_processing import (
    _MAX_NAME_WIDTH,
    _MIN_ELISION_SAVINGS,
    USER_ABORT_EXCEPTIONS,
    BatchPassResult,
    _elide_middle,
    perform_cleanup,
    run_batch_upload,
    upload_files_from_list,
)
from ghga_connector.core.uploading.structs import (
    CoreFileInfo,
    FileInfoForUpload,
    UploadedFileInfo,
)
from tests.fixtures.utils import (
    TEST_STORAGE_ALIAS1,
    make_file_info_for_upload,
    make_mock_uploader,
)

pytestmark = pytest.mark.asyncio


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
            file_alias="test-file", exception=RuntimeError("something went wrong")
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


@pytest.mark.parametrize("overwrite", [True, False])
async def test_upload_files_from_list_applies_overwrite(overwrite: bool):
    """Test that the overwrite flag is forwarded to every file's Uploader."""
    with NamedTemporaryFile() as f1, NamedTemporaryFile() as f2:
        file_infos = [
            make_file_info_for_upload(path=Path(f1.name), alias="first"),
            make_file_info_for_upload(path=Path(f2.name), alias="second"),
        ]
        mock_uploader = make_mock_uploader()

        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.Uploader",
                return_value=mock_uploader,
            ) as mock_uploader_cls,
            patch("ghga_connector.core.uploading.batch_processing.Crypt4GHEncryptor"),
        ):
            await upload_files_from_list(
                upload_client=AsyncMock(),
                file_info_list=file_infos,
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
                overwrite=overwrite,
            )

        overwrite_kwargs = [
            call.kwargs["overwrite"] for call in mock_uploader_cls.call_args_list
        ]
        assert overwrite_kwargs == [overwrite, overwrite]


@pytest.mark.parametrize("delete_raises", [None, RuntimeError("delete failed")])
async def test_perform_cleanup_restores_sigint_handler(delete_raises):
    """perform_cleanup must restore the previous SIGINT handler afterward, both on a
    successful delete and when delete_file() raises, so Ctrl+C keeps working for the
    rest of the batch.
    """
    sentinel_handler = signal.getsignal(signal.SIGINT)
    uploader = AsyncMock()
    if delete_raises is not None:
        uploader.delete_file.side_effect = delete_raises

    await perform_cleanup(uploader=uploader, alias="some-file")

    assert signal.getsignal(signal.SIGINT) is sentinel_handler


async def test_stop_during_a_failing_deletion_leaves_no_loop_error():
    """A stop while the deletion runs lets it finish, and its error leaves nothing
    for asyncio to report as unhandled.
    """

    async def failing_delete() -> None:
        await asyncio.sleep(0.1)
        raise RuntimeError("DELETE failed")

    uploader = AsyncMock()
    uploader.delete_file.side_effect = failing_delete
    errors: list[str] = []
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()
    loop.set_exception_handler(lambda _loop, context: errors.append(context["message"]))
    try:
        cleanup = asyncio.create_task(perform_cleanup(uploader=uploader, alias="f0"))
        await asyncio.sleep(0.01)
        cleanup.cancel()
        assert await cleanup
    finally:
        loop.set_exception_handler(previous_handler)

    uploader.delete_file.assert_awaited_once()
    assert errors == []


async def test_upload_files_from_list_halts_on_abort_during_init():
    """Test that keyboard cancel during initiate_file_upload() stops batch processing
    and performs cleanup. The current and remaining files should be listed as failed.
    """
    # Create a couple of test files to upload
    with NamedTemporaryFile() as f1, NamedTemporaryFile() as f2:
        file_infos = [
            make_file_info_for_upload(path=Path(f1.name), alias="first"),
            make_file_info_for_upload(path=Path(f2.name), alias="second"),
        ]

        # Rig a mock uploader to error during initiation
        aborting_uploader = AsyncMock()
        aborting_uploader.initiate_file_upload.side_effect = KeyboardInterrupt
        second_uploader = make_mock_uploader()

        # Patch in the exploding mock uploader
        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.Uploader",
                side_effect=[aborting_uploader, second_uploader],
            ),
        ):
            result = await upload_files_from_list(
                upload_client=AsyncMock(),
                file_info_list=file_infos,
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
            )

        # Inspect the captured result and verify that `halted` is set to True
        assert result.halted

        # Make sure both files are reported as failed but no cleanup was done for the
        #  second file because it was of course not started
        assert [fi.alias for fi in result.failed] == ["first", "second"]
        second_uploader.initiate_file_upload.assert_not_called()
        aborting_uploader.delete_file.assert_not_called()


@pytest.mark.parametrize("abort", USER_ABORT_EXCEPTIONS)
async def test_upload_files_from_list_halts_on_abort_during_upload(
    abort: BaseException,
):
    """Test that keyboard cancel during upload_file() stops batch processing and
    performs cleanup. The current and remaining files should be listed as failed.
    """
    # Set up two test files and the rigged-to-blow Mock Uploader
    with NamedTemporaryFile() as f1, NamedTemporaryFile() as f2:
        file_infos = [
            make_file_info_for_upload(path=Path(f1.name), alias="first"),
            make_file_info_for_upload(path=Path(f2.name), alias="second"),
        ]
        aborting_uploader = make_mock_uploader(upload_raises=abort)
        second_uploader = make_mock_uploader()

        # Patch in the mock uploader, but also mock the encryptor since it gets called
        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.Uploader",
                side_effect=[aborting_uploader, second_uploader],
            ),
            patch("ghga_connector.core.uploading.batch_processing.Crypt4GHEncryptor"),
        ):
            result = await upload_files_from_list(
                upload_client=AsyncMock(),
                file_info_list=file_infos,
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
            )

        # Inspect the results - make sure halted=True, and only first file cleaned up
        assert result.halted
        assert [fi.alias for fi in result.failed] == ["first", "second"]
        aborting_uploader.delete_file.assert_called_once()
        second_uploader.initiate_file_upload.assert_not_called()


async def test_upload_process_stops_on_failure():
    """Make sure that when initiate_file_upload() fails because the FileUploadBox lacks
    sufficient space, the batch stops, delete_file is NOT called (nothing to clean up),
    remaining files are skipped, and the function returns cleanly
    (no unhandled exception propagating to the caller).
    """
    with NamedTemporaryFile() as f1, NamedTemporaryFile() as f2:
        file_infos = [
            make_file_info_for_upload(path=Path(f1.name), alias="file-one"),
            make_file_info_for_upload(path=Path(f2.name), alias="file-two"),
        ]

        def _error():
            """Simulate error chain/re-raising of UploadBoxSizeExceededError"""
            try:
                raise exceptions.UploadBoxSizeExceededError(
                    file_alias="file-one", file_upload_box_id=uuid4()
                )
            except Exception as exc:
                raise exceptions.CreateFileUploadError(
                    file_alias="file-one", exception=exc
                ) from exc

        failing_uploader = AsyncMock()
        failing_uploader.initiate_file_upload.side_effect = _error
        second_uploader = make_mock_uploader()

        # Patch the Uploader and message display
        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.Uploader",
                side_effect=[failing_uploader, second_uploader],
            ),
            patch(
                "ghga_connector.core.uploading.batch_processing.CLIMessageDisplay"
            ) as mock_display,
        ):
            # Must return without raising
            await upload_files_from_list(
                upload_client=AsyncMock(),
                file_info_list=file_infos,
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
            )

        failing_uploader.delete_file.assert_not_called()
        # Second file must not be started
        second_uploader.initiate_file_upload.assert_not_called()
        second_uploader.upload_file.assert_not_called()

        # Verify the user sees the error detail and the stop notification
        failure_messages = [
            call.args[0] for call in mock_display.failure.call_args_list
        ]
        assert any("file-one" in msg for msg in failure_messages)
        assert (
            "Upload process stopped."
            " If applicable, any previously completed file uploads remain uploaded."
        ) in failure_messages


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


async def test_upload_files_from_list_rejects_encrypted_file():
    """Ensure a file that is already Crypt4GH-encrypted is rejected when it is its turn,
    without initiating a server-side upload, and does not stop the rest of the batch.
    """
    crypt4gh_header = b"crypt4gh" + b"\x01\x00\x00\x00"
    with NamedTemporaryFile() as encrypted, NamedTemporaryFile() as plain:
        encrypted.write(crypt4gh_header)
        encrypted.flush()
        file_infos = [
            make_file_info_for_upload(path=Path(encrypted.name), alias="encrypted"),
            make_file_info_for_upload(path=Path(plain.name), alias="plain"),
        ]
        mock_uploader = make_mock_uploader()

        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.Uploader",
                return_value=mock_uploader,
            ),
            patch("ghga_connector.core.uploading.batch_processing.Crypt4GHEncryptor"),
            patch(
                "ghga_connector.core.uploading.batch_processing.CLIMessageDisplay"
            ) as mock_display,
        ):
            result = await upload_files_from_list(
                upload_client=AsyncMock(),
                file_info_list=file_infos,
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
            )

        # The encrypted file is rejected (not failed) and the plain file still uploads:
        assert not result.halted
        assert [fi.alias for fi in result.rejected] == ["encrypted"]
        assert result.failed == []
        mock_uploader.initiate_file_upload.assert_called_once()
        mock_uploader.upload_file.assert_called_once()

        failure_messages = [
            str(call.args[0]) for call in mock_display.failure.call_args_list
        ]
        assert any("already Crypt4GH encrypted" in msg for msg in failure_messages)


async def test_upload_files_from_list_fails_unreadable_file():
    """Test that a file that cannot be read when it's about to be processed is reported
    as failed instead of crashing the batch.
    """
    with NamedTemporaryFile() as f:
        missing = make_file_info_for_upload(
            path=Path(f.name).parent / "no-such-file.bam", alias="gone"
        )
        present = make_file_info_for_upload(path=Path(f.name), alias="present")
        mock_uploader = make_mock_uploader()

        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.Uploader",
                return_value=mock_uploader,
            ),
            patch("ghga_connector.core.uploading.batch_processing.Crypt4GHEncryptor"),
            patch("ghga_connector.core.uploading.batch_processing.CLIMessageDisplay"),
        ):
            result = await upload_files_from_list(
                upload_client=AsyncMock(),
                file_info_list=[missing, present],
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
            )

        assert not result.halted
        assert [fi.alias for fi in result.failed] == ["gone"]
        assert result.rejected == []
        mock_uploader.initiate_file_upload.assert_called_once()


async def test_upload_files_from_list_reports_failures():
    """Make sure that if a file upload results in an error, the file is returned in the
    result's failed list.
    """
    with NamedTemporaryFile() as f1, NamedTemporaryFile() as f2:
        file_infos = [
            make_file_info_for_upload(path=Path(f1.name), alias="ok"),
            make_file_info_for_upload(path=Path(f2.name), alias="bad"),
        ]
        good_uploader = make_mock_uploader()
        bad_uploader = make_mock_uploader(upload_raises=RuntimeError("problem"))

        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.Uploader",
                side_effect=[good_uploader, bad_uploader],
            ),
            patch("ghga_connector.core.uploading.batch_processing.Crypt4GHEncryptor"),
        ):
            result = await upload_files_from_list(
                upload_client=AsyncMock(),
                file_info_list=file_infos,
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
            )

        assert not result.halted
        assert [fi.alias for fi in result.failed] == ["bad"]


async def test_upload_files_from_list_halts_on_box_full():
    """Test that when the box is full, processing stops and reports remaining files as failed."""
    with NamedTemporaryFile() as f1, NamedTemporaryFile() as f2:
        file_infos = [
            make_file_info_for_upload(path=Path(f1.name), alias="first"),
            make_file_info_for_upload(path=Path(f2.name), alias="second"),
        ]

        def _box_full():
            try:
                raise exceptions.UploadBoxSizeExceededError(
                    file_alias="first", file_upload_box_id=uuid4()
                )
            except Exception as exc:
                raise exceptions.CreateFileUploadError(
                    file_alias="first", exception=exc
                ) from exc

        failing_uploader = AsyncMock()
        failing_uploader.initiate_file_upload.side_effect = _box_full
        second_uploader = make_mock_uploader()

        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.Uploader",
                side_effect=[failing_uploader, second_uploader],
            ),
            patch("ghga_connector.core.uploading.batch_processing.Crypt4GHEncryptor"),
        ):
            result = await upload_files_from_list(
                upload_client=AsyncMock(),
                file_info_list=file_infos,
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
            )

        assert result.halted
        # Both the file that triggered the error and the un-attempted file are reported.
        assert [fi.alias for fi in result.failed] == ["first", "second"]
        second_uploader.initiate_file_upload.assert_not_called()


async def test_upload_files_from_list_shortens_alias_in_messages():
    """With shorten=True, long aliases are middle-elided in live upload messages."""
    long_alias = "sample-" + "z" * 90
    with NamedTemporaryFile() as f:
        file_info = make_file_info_for_upload(path=Path(f.name), alias=long_alias)
        mock_uploader = make_mock_uploader()

        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.Uploader",
                return_value=mock_uploader,
            ) as mock_uploader_cls,
            patch("ghga_connector.core.uploading.batch_processing.Crypt4GHEncryptor"),
            patch(
                "ghga_connector.core.uploading.batch_processing.CLIMessageDisplay"
            ) as mock_display,
        ):
            await upload_files_from_list(
                upload_client=AsyncMock(),
                file_info_list=[file_info],
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
                shorten=True,
            )

        messages = " ".join(
            str(call.args[0]) for call in mock_display.success.call_args_list
        )
        assert " … " in messages  # the alias was elided
        assert long_alias not in messages

        # The progress bar (Uploader.display_name) also gets the elided name, while the
        # full alias is preserved for the API calls.
        display_name = mock_uploader_cls.call_args.kwargs["display_name"]
        assert " … " in display_name
        assert long_alias not in display_name


def _make_upload_client(box_contents: list[UploadedFileInfo]) -> AsyncMock:
    """Create a mock UploadClient whose get_box_uploads returns box_contents."""
    upload_client = AsyncMock()
    upload_client.get_box_uploads.return_value = box_contents
    return upload_client


async def test_run_batch_upload_skips_already_uploaded():
    """Files already present (non-cancelled) in the box are not re-uploaded."""
    with NamedTemporaryFile() as f1, NamedTemporaryFile() as f2:
        file_infos = [
            make_file_info_for_upload(path=Path(f1.name), alias="already"),
            make_file_info_for_upload(path=Path(f2.name), alias="fresh"),
        ]
        upload_client = _make_upload_client(
            [UploadedFileInfo(file_id=uuid4(), alias="already", state="interrogated")]
        )

        captured: list[list[str]] = []

        async def fake_batch_cycle(*, file_info_list, **_kwargs):
            captured.append([fi.alias for fi in file_info_list])
            return BatchPassResult(failed=[], halted=False)

        with patch(
            "ghga_connector.core.uploading.batch_processing.upload_files_from_list",
            fake_batch_cycle,
        ):
            await run_batch_upload(
                upload_client=upload_client,
                file_info_list=file_infos,
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
                max_retries=0,
            )

        # Only the fresh file should have been passed to the uploader.
        assert captured == [["fresh"]]


async def test_run_batch_upload_does_not_skip_cancelled_or_failed():
    """Cancelled and failed aliases in the box are re-uploaded, not skipped."""
    with NamedTemporaryFile() as f1, NamedTemporaryFile() as f2:
        file_infos = [
            make_file_info_for_upload(path=Path(f1.name), alias="cancelled-file"),
            make_file_info_for_upload(path=Path(f2.name), alias="failed-file"),
        ]
        upload_client = _make_upload_client(
            [
                UploadedFileInfo(
                    file_id=uuid4(), alias="cancelled-file", state="cancelled"
                ),
                UploadedFileInfo(file_id=uuid4(), alias="failed-file", state="failed"),
            ]
        )

        captured: list[list[str]] = []

        async def fake_batch_cycle(*, file_info_list, **_kwargs):
            captured.extend([fi.alias for fi in file_info_list])
            return BatchPassResult(failed=[], halted=False)

        with patch(
            "ghga_connector.core.uploading.batch_processing.upload_files_from_list",
            fake_batch_cycle,
        ):
            await run_batch_upload(
                upload_client=upload_client,
                file_info_list=file_infos,
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
                max_retries=0,
            )

        assert captured == ["cancelled-file", "failed-file"]


@pytest.mark.parametrize("overwrite", [True, False])
async def test_run_batch_upload_applies_overwrite(overwrite: bool):
    """Test that the user-supplied overwrite flag is applied to each upload pass.

    This is similar to test_upload_files_from_list_applies_overwrite but checks at the
    batch cycle level.
    """
    with NamedTemporaryFile() as f:
        file_infos = [make_file_info_for_upload(path=Path(f.name), alias="fresh-file")]
        upload_client = _make_upload_client([])

        captured: list[bool] = []

        async def fake_batch_cycle(*, overwrite, **_kwargs):
            captured.append(overwrite)
            return BatchPassResult(failed=[], halted=False)

        with patch(
            "ghga_connector.core.uploading.batch_processing.upload_files_from_list",
            fake_batch_cycle,
        ):
            await run_batch_upload(
                upload_client=upload_client,
                file_info_list=file_infos,
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
                max_retries=0,
                overwrite=overwrite,
            )

        assert captured == [overwrite]


async def test_run_batch_upload_all_skipped_does_not_upload():
    """When every file is already uploaded, no upload pass is attempted."""
    with NamedTemporaryFile() as f:
        file_infos = [make_file_info_for_upload(path=Path(f.name), alias="done")]
        upload_client = _make_upload_client(
            [UploadedFileInfo(file_id=uuid4(), alias="done", state="interrogated")]
        )

        fake_batch_cycle = AsyncMock()
        with patch(
            "ghga_connector.core.uploading.batch_processing.upload_files_from_list",
            fake_batch_cycle,
        ):
            await run_batch_upload(
                upload_client=upload_client,
                file_info_list=file_infos,
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
                max_retries=3,
            )

        fake_batch_cycle.assert_not_called()


async def test_run_batch_upload_dry_run_does_not_upload():
    """In dry-run mode, already-uploaded files are still skipped but nothing uploads."""
    with NamedTemporaryFile() as f1, NamedTemporaryFile() as f2:
        file_infos = [
            make_file_info_for_upload(path=Path(f1.name), alias="already"),
            make_file_info_for_upload(path=Path(f2.name), alias="fresh"),
        ]
        upload_client = _make_upload_client(
            [UploadedFileInfo(file_id=uuid4(), alias="already", state="interrogated")]
        )

        fake_batch_cycle = AsyncMock()
        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.upload_files_from_list",
                fake_batch_cycle,
            ),
            patch(
                "ghga_connector.core.uploading.batch_processing.CLIMessageDisplay"
            ) as mock_display,
        ):
            await run_batch_upload(
                upload_client=upload_client,
                file_info_list=file_infos,
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
                max_retries=3,
                dry_run=True,
            )

        # No upload pass is attempted in dry-run mode.
        fake_batch_cycle.assert_not_called()

        # The box is still queried so already-uploaded files are reported as skipped.
        upload_client.get_box_uploads.assert_awaited_once()
        messages = " ".join(
            str(call.args[0]) for call in mock_display.display.call_args_list
        )
        assert "Dry run" in messages
        # The fresh file is listed as one that would be uploaded; the skipped one is not.
        assert "fresh" in messages
        assert "Skipping 1 file(s)" in messages


async def test_run_batch_upload_dry_run_aligns_columns(tmp_path):
    """Dry-run file rows align their arrow, path and size columns vertically."""
    short = tmp_path / "a.bam"
    short.write_bytes(b"x")
    longer = tmp_path / "much-longer-name.bam"
    longer.write_bytes(b"x" * 2048)
    file_infos = [
        make_file_info_for_upload(path=short, alias="a", decrypted_size=1),
        make_file_info_for_upload(
            path=longer, alias="longer-alias", decrypted_size=2048
        ),
    ]

    with (
        patch(
            "ghga_connector.core.uploading.batch_processing.upload_files_from_list",
            AsyncMock(),
        ),
        patch(
            "ghga_connector.core.uploading.batch_processing.CLIMessageDisplay"
        ) as mock_display,
    ):
        await run_batch_upload(
            upload_client=_make_upload_client([]),
            file_info_list=file_infos,
            my_private_key=SecretBytes(b"\x00" * 32),
            max_concurrent_uploads=1,
            dry_run=True,
        )

    all_lines = [str(call.args[0]) for call in mock_display.display.call_args_list]
    lines = [line for line in all_lines if line.startswith("  - ")]
    assert len(lines) == 2
    # The arrow and both parentheses occupy the same column in every row.
    assert len({line.index("->") for line in lines}) == 1
    assert len({line.index("(") for line in lines}) == 1
    assert len({line.index(")") for line in lines}) == 1

    # A header row labels the columns and lines up over them.
    header = next(line for line in all_lines if "ALIAS" in line)
    assert "PATH" in header and "SIZE" in header
    assert header.index("ALIAS") == len("  - ")
    assert header.index("PATH") == lines[0].index("->") + len("->  ")
    assert header.index("SIZE") + len("SIZE") == lines[0].index(")")


async def _dry_run_lines(file_infos, *, shorten):
    """Run a dry-run and return the per-file table rows that were displayed."""
    with (
        patch(
            "ghga_connector.core.uploading.batch_processing.upload_files_from_list",
            AsyncMock(),
        ),
        patch(
            "ghga_connector.core.uploading.batch_processing.CLIMessageDisplay"
        ) as mock_display,
    ):
        await run_batch_upload(
            upload_client=_make_upload_client([]),
            file_info_list=file_infos,
            my_private_key=SecretBytes(b"\x00" * 32),
            max_concurrent_uploads=1,
            dry_run=True,
            shorten=shorten,
        )
    return [
        str(call.args[0])
        for call in mock_display.display.call_args_list
        if str(call.args[0]).startswith("  - ")
    ]


async def test_elide_middle_keeps_text_below_savings_threshold():
    """An alias only marginally over the width limit is returned unchanged, since
    eliding it would hide content for little width benefit.
    """
    # One char short of the point where eliding would save _MIN_ELISION_SAVINGS chars.
    text = "a" * (_MAX_NAME_WIDTH + _MIN_ELISION_SAVINGS - 1)
    assert _elide_middle(text) == text


async def test_elide_middle_elides_once_savings_threshold_met():
    """Once eliding saves at least _MIN_ELISION_SAVINGS chars, the alias is middle-elided
    down to the width limit.
    """
    text = "head" + "x" * (_MAX_NAME_WIDTH + _MIN_ELISION_SAVINGS) + "tail"
    assert len(text) >= _MAX_NAME_WIDTH + _MIN_ELISION_SAVINGS

    result = _elide_middle(text)

    assert result != text
    assert len(result) == _MAX_NAME_WIDTH
    assert " … " in result
    assert result.startswith("head")
    assert result.endswith("tail")


async def test_run_batch_upload_dry_run_elides_long_alias_when_shortened():
    """With shorten=True, very long aliases are middle-elided but paths are shown
    in full.
    """
    long_alias = "alias-" + "x" * 90
    long_path = Path("/data/" + "deep/" * 30 + "final-file.bam")
    file_infos = [
        make_file_info_for_upload(path=long_path, alias=long_alias, decrypted_size=10)
    ]

    (line,) = await _dry_run_lines(file_infos, shorten=True)

    # The alias is elided, keeping its start and end, while the path is left intact.
    assert " … " in line  # ellipsis is surrounded by spaces
    assert long_alias not in line
    assert long_alias[:10] in line  # head of the alias kept
    assert str(long_path) in line  # path is never elided


async def test_run_batch_upload_dry_run_shows_full_names_by_default():
    """With shorten=False (default), long aliases and paths are shown in full."""
    long_alias = "alias-" + "x" * 90
    long_path = Path("/data/" + "deep/" * 30 + "final-file.bam")
    file_infos = [
        make_file_info_for_upload(path=long_path, alias=long_alias, decrypted_size=10)
    ]

    (line,) = await _dry_run_lines(file_infos, shorten=False)

    assert "…" not in line
    assert long_alias in line
    assert str(long_path) in line


async def test_run_batch_upload_elides_long_skip_list():
    """A long list of already-uploaded files is elided in the skip message."""
    file_infos = [
        make_file_info_for_upload(path=Path(f"/tmp/file-{i}.bam"), alias=f"file-{i}")
        for i in range(12)
    ]
    box = [
        UploadedFileInfo(file_id=uuid4(), alias=f"file-{i}", state="interrogated")
        for i in range(12)
    ]
    with patch(
        "ghga_connector.core.uploading.batch_processing.CLIMessageDisplay"
    ) as mock_display:
        await run_batch_upload(
            upload_client=_make_upload_client(box),
            file_info_list=file_infos,
            my_private_key=SecretBytes(b"\x00" * 32),
            max_concurrent_uploads=1,
        )

    messages = " ".join(
        str(call.args[0]) for call in mock_display.display.call_args_list
    )
    assert "Skipping 12 file(s)" in messages
    # Only the first 10 aliases are listed; the remainder are summarized.
    assert "(+2 more)" in messages
    assert "file-11" not in messages


async def test_run_batch_upload_retries_failures():
    """Failed files are retried, and a retry that succeeds ends the loop."""
    with NamedTemporaryFile() as f:
        failing = make_file_info_for_upload(path=Path(f.name), alias="flaky")
        upload_client = _make_upload_client([])

        calls: list[list[str]] = []

        async def fake_batch_cycle(*, file_info_list, **_kwargs):
            calls.append([fi.alias for fi in file_info_list])
            # Fail on the first pass, succeed on the retry.
            if len(calls) == 1:
                return BatchPassResult(failed=[failing], halted=False)
            return BatchPassResult(failed=[], halted=False)

        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.upload_files_from_list",
                fake_batch_cycle,
            ),
            patch(
                "ghga_connector.core.uploading.batch_processing.asyncio.sleep",
                AsyncMock(),
            ),
        ):
            await run_batch_upload(
                upload_client=upload_client,
                file_info_list=[failing],
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
                max_retries=3,
            )

        assert calls == [["flaky"], ["flaky"]]


async def test_run_batch_upload_does_not_retry_rejected_files():
    """Files rejected as already encrypted are not retried, are reported at the end,
    and suppress the all-files-uploaded success message.
    """
    with NamedTemporaryFile() as f:
        rejected = make_file_info_for_upload(path=Path(f.name), alias="pre-encrypted")
        upload_client = _make_upload_client([])

        call_count = 0

        async def fake_batch_cycle(*, file_info_list, **_kwargs):
            nonlocal call_count
            call_count += 1
            return BatchPassResult(failed=[], rejected=[rejected], halted=False)

        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.upload_files_from_list",
                fake_batch_cycle,
            ),
            patch(
                "ghga_connector.core.uploading.batch_processing.CLIMessageDisplay"
            ) as mock_display,
        ):
            await run_batch_upload(
                upload_client=upload_client,
                file_info_list=[rejected],
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
                max_retries=3,
            )

        # No retry pass is attempted for a rejected file.
        assert call_count == 1

        failure_messages = [
            str(call.args[0]) for call in mock_display.failure.call_args_list
        ]
        assert any(
            "already Crypt4GH encrypted" in msg and "pre-encrypted" in msg
            for msg in failure_messages
        )
        mock_display.success.assert_not_called()


async def test_run_batch_upload_stops_after_max_retries():
    """Persistent failures stop after the initial pass plus max_retries retries."""
    with NamedTemporaryFile() as f:
        failing = make_file_info_for_upload(path=Path(f.name), alias="doomed")
        upload_client = _make_upload_client([])

        call_count = 0

        async def fake_batch_cycle(*, file_info_list, **_kwargs):
            nonlocal call_count
            call_count += 1
            return BatchPassResult(failed=[failing], halted=False)

        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.upload_files_from_list",
                fake_batch_cycle,
            ),
            patch(
                "ghga_connector.core.uploading.batch_processing.asyncio.sleep",
                AsyncMock(),
            ) as mock_sleep,
        ):
            await run_batch_upload(
                upload_client=upload_client,
                file_info_list=[failing],
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
                max_retries=2,
            )

        # 1 initial pass + 2 retries
        assert call_count == 3
        # One backoff wait precedes each of the 2 retries.
        assert mock_sleep.await_count == 2
        assert mock_sleep.await_args_list[0].args == (BATCH_RETRY_BACKOFF_SEC,)


async def test_run_batch_upload_does_not_retry_when_halted():
    """A halted pass (e.g. box full) is not retried even if retries remain."""
    with NamedTemporaryFile() as f:
        failing = make_file_info_for_upload(path=Path(f.name), alias="halt-me")
        upload_client = _make_upload_client([])

        call_count = 0

        async def fake_batch_cycle(*, file_info_list, **_kwargs):
            nonlocal call_count
            call_count += 1
            return BatchPassResult(failed=[failing], halted=True)

        with patch(
            "ghga_connector.core.uploading.batch_processing.upload_files_from_list",
            fake_batch_cycle,
        ):
            await run_batch_upload(
                upload_client=upload_client,
                file_info_list=[failing],
                my_private_key=SecretBytes(b"\x00" * 32),
                max_concurrent_uploads=1,
                max_retries=5,
            )

        assert call_count == 1


# --- Several files in flight ------------------------------------------------------------

MiB = 1024**2


class RecordingUploadClient:
    """An upload client that records which parts are in flight, per file and overall.

    Each part upload takes `part_seconds`. A file whose alias is in `failing` fails on
    its first part, and one in `box_full` is refused on create as too large for the box.
    A create takes `create_seconds`, also when refused; an accepted upload is opened
    first, as UCS answers after it has created the upload. An overwrite
    replaces the alias's upload in `others_open`, which UCS allows at its limit. A
    deletion counts only once its `delete_seconds` passed.
    """

    def __init__(
        self,
        *,
        part_seconds: float = 0.02,
        failing: tuple[str, ...] = (),
        box_full: tuple[str, ...] = (),
        open_limit: int | None = None,
        others_open: tuple[str, ...] = (),
        busy_once: tuple[str, ...] = (),
        create_seconds: float = 0,
        delete_seconds: float = 0,
    ):
        self._part_seconds = part_seconds
        self._create_seconds = create_seconds
        self._delete_seconds = delete_seconds
        self._failing = failing
        self._box_full = box_full
        # UCS's limit of open uploads per box, which also counts other uploads
        self._open_limit = open_limit
        self._others_open = others_open
        self.creating_now = 0
        self.max_creating = 0
        # Files whose first create is answered with a plain 429
        self._busy_once = set(busy_once)
        self.open_now = 0
        self.max_open = 0
        self.aliases: dict = {}
        self.created: list[str] = []
        self.completed: list[str] = []
        self.deleted: list[str] = []
        self.in_flight: dict[str, int] = {}
        self.max_total = 0
        self.max_per_file = 0
        self.parts_started = asyncio.Event()
        self.creates_started = asyncio.Event()
        self.deletes_started = asyncio.Event()

    async def create_file_upload(self, *, file_alias, overwrite=False, **_kwargs):
        """Open an upload, or refuse it if the box is full."""
        self.creating_now += 1
        self.max_creating = max(self.max_creating, self.creating_now)
        try:
            return await self._create(file_alias=file_alias, overwrite=overwrite)
        finally:
            self.creating_now -= 1

    async def _create(self, *, file_alias, overwrite):
        """Answer a create as UCS does."""
        if file_alias in self._box_full:
            raise exceptions.UploadBoxSizeExceededError(
                file_alias=file_alias, file_upload_box_id=uuid4()
            )
        if file_alias in self._busy_once:
            self._busy_once.discard(file_alias)
            raise exceptions.TooManyRequestsError()
        if overwrite and file_alias in self._others_open:
            self._others_open = tuple(a for a in self._others_open if a != file_alias)
        if (
            self._open_limit is not None
            and len(self._others_open) + self.open_now >= self._open_limit
        ):
            if self._create_seconds:
                await asyncio.sleep(self._create_seconds)
            raise exceptions.TooManyOpenUploadsError(file_alias=file_alias)
        file_id = uuid4()
        self.aliases[file_id] = file_alias
        self.created.append(file_alias)
        self.open_now += 1
        self.max_open = max(self.max_open, self.open_now)
        self.creates_started.set()
        if self._create_seconds:
            await asyncio.sleep(self._create_seconds)
        return file_id, TEST_STORAGE_ALIAS1

    async def get_box_uploads(self):
        """List the other open uploads in the box."""
        return [
            UploadedFileInfo(file_id=uuid4(), alias=alias, state="init")
            for alias in self._others_open
        ]

    async def get_part_upload_url(self, *, file_id, part_no):
        """Return a URL for any part."""
        return f"https://s3.invalid/{file_id}/{part_no}"

    async def upload_file_part(self, *, file_id, content, part_no, url=None):
        """Hold the part for a while, recording what is in flight meanwhile."""
        alias = self.aliases[file_id]
        if alias in self._failing:
            raise RuntimeError(f"S3 refused a part of {alias}")
        self.in_flight[alias] = self.in_flight.get(alias, 0) + 1
        self.max_per_file = max(self.max_per_file, self.in_flight[alias])
        self.max_total = max(self.max_total, sum(self.in_flight.values()))
        self.parts_started.set()
        try:
            await asyncio.sleep(self._part_seconds)
        finally:
            self.in_flight[alias] -= 1

    async def complete_file_upload(self, *, file_alias, **_kwargs):
        """Record the completed file."""
        self.completed.append(file_alias)
        self.open_now -= 1

    async def delete_file(self, *, file_id, file_alias):
        """Record the deleted file."""
        self.deletes_started.set()
        if self._delete_seconds:
            await asyncio.sleep(self._delete_seconds)
        self.deleted.append(file_alias)
        self.open_now -= 1


def make_files_in_flight(
    directory: Path, part_counts: dict[str, int]
) -> list[FileInfoForUpload]:
    """Make files with the given part counts, in the given order."""
    file_infos = []
    for alias, parts in part_counts.items():
        path = directory / alias
        path.write_bytes(b"plaintext")
        file_info = make_file_info_for_upload(
            path=path, alias=alias, decrypted_size=parts * 5 * MiB - MiB
        )
        assert file_info.part_count == parts
        file_infos.append(file_info)
    return file_infos


def fake_encryptor(**kwargs) -> MagicMock:
    """An encryptor that yields as many small parts as the file is to have."""
    file_info = CoreFileInfo(
        alias="x", path=Path("/dev/null"), decrypted_size=kwargs["file_size"]
    )
    part_count = math.ceil(file_info.encrypted_size / kwargs["part_size"])
    encryptor = MagicMock()
    encryptor.checksums = Checksums()
    encryptor.process_file.return_value = iter(
        [(n, bytearray(b"part")) for n in range(1, part_count + 1)]
    )
    return encryptor


async def upload_in_flight(client, file_infos, *, parts: int, files: int, **options):
    """Run one pass with the recording client and the fake encryptor."""
    with patch(
        "ghga_connector.core.uploading.batch_processing.Crypt4GHEncryptor",
        side_effect=fake_encryptor,
    ):
        return await upload_files_from_list(
            upload_client=client,
            file_info_list=file_infos,
            my_private_key=SecretBytes(b"\x00" * 32),
            max_concurrent_uploads=parts,
            max_concurrent_files=files,
            **options,
        )


async def test_files_in_flight_share_the_budget(tmp_path: Path):
    """Several files upload at once, largest first, within the budget and each file
    within its share of it.
    """
    part_counts = {"small": 2, "large": 6, "medium": 4, "tiny": 1, "big": 5}
    file_infos = make_files_in_flight(tmp_path, part_counts)
    client = RecordingUploadClient()

    result = await upload_in_flight(client, file_infos, parts=5, files=3)

    assert result == BatchPassResult()
    assert client.created == ["large", "big", "medium", "small", "tiny"]
    assert sorted(client.completed) == sorted(part_counts)
    assert client.max_total <= 5
    assert client.max_per_file <= 2  # ceil(5 / 3)
    assert client.max_total > client.max_per_file  # files were in flight together


async def test_failed_file_leaves_the_others_running(tmp_path: Path):
    """A file that fails is deleted while the others finish."""
    file_infos = make_files_in_flight(tmp_path, {"one": 3, "bad": 3, "three": 3})
    client = RecordingUploadClient(failing=("bad",))

    result = await upload_in_flight(client, file_infos, parts=6, files=3)

    assert [fi.alias for fi in result.failed] == ["bad"]
    assert not result.halted
    assert client.deleted == ["bad"]
    assert sorted(client.completed) == ["one", "three"]


async def test_abort_deletes_every_file_in_flight(tmp_path: Path):
    """Cancelling the pass, as Ctrl+C does, deletes every file in flight, halts the
    batch and leaves the SIGINT handler as it was.
    """
    sigint_handler = signal.getsignal(signal.SIGINT)
    file_infos = make_files_in_flight(tmp_path, {f"file-{i}": 3 for i in range(5)})
    client = RecordingUploadClient(part_seconds=10)

    task = asyncio.create_task(upload_in_flight(client, file_infos, parts=6, files=3))
    await asyncio.wait_for(client.parts_started.wait(), timeout=5)
    await asyncio.sleep(0.05)  # let the other files start their parts
    task.cancel()
    result = await task

    assert result.halted
    assert len(client.created) == 3
    assert sorted(client.deleted) == sorted(client.created)
    assert client.completed == []
    assert [fi.alias for fi in result.failed] == [fi.alias for fi in file_infos]
    assert signal.getsignal(signal.SIGINT) is sigint_handler


async def test_full_box_lets_files_in_flight_finish(tmp_path: Path):
    """A full box starts no further file, lets the files in flight finish, and
    halts the batch with the rest failed.
    """
    file_infos = make_files_in_flight(
        tmp_path, {"first": 4, "second": 3, "refused": 2, "never": 1}
    )
    client = RecordingUploadClient(box_full=("refused",))

    result = await upload_in_flight(client, file_infos, parts=4, files=2)

    assert result.halted
    assert sorted(client.completed) == ["first", "second"]
    assert client.created == ["first", "second"]
    assert [fi.alias for fi in result.failed] == ["refused", "never"]
    assert client.deleted == []


async def test_box_with_one_free_upload_slot_ends_the_batch(tmp_path: Path):
    """With four other uploads open in a box that accepts five, the batch uploads its
    files one at a time and then ends.
    """
    file_infos = make_files_in_flight(tmp_path, {f"file-{i}": 1 for i in range(6)})
    client = RecordingUploadClient(
        open_limit=5,
        others_open=tuple(f"stale-{i}" for i in range(4)),
        create_seconds=0.01,
    )

    # Waits without cancelling, since a cancelled pass returns as if it had ended
    batch = asyncio.create_task(upload_in_flight(client, file_infos, parts=10, files=4))
    done, _ = await asyncio.wait({batch}, timeout=5)
    if not done:
        batch.cancel()
        await asyncio.wait({batch})
    assert done, "the batch is still running after its last file"
    result = batch.result()

    assert sorted(client.completed) == sorted(fi.alias for fi in file_infos)
    assert result.failed == []
    assert client.max_open == 1


async def test_lone_file_gets_every_part_slot(tmp_path: Path):
    """A batch of one file uploads it with all the parts the budget allows."""
    file_infos = make_files_in_flight(tmp_path, {"lone": 12})
    client = RecordingUploadClient()

    await upload_in_flight(client, file_infos, parts=10, files=4)

    assert client.max_per_file == 10


async def test_box_at_its_upload_limit_holds_files_back(tmp_path: Path):
    """With two other uploads open in a box that accepts five, at most three of the
    batch's files are open at once, and no file fails for the limit.
    """
    file_infos = make_files_in_flight(tmp_path, {f"file-{i}": 2 for i in range(6)})
    client = RecordingUploadClient(open_limit=5, others_open=("stale-1", "stale-2"))

    result = await upload_in_flight(client, file_infos, parts=8, files=4)

    assert result == BatchPassResult()
    assert sorted(client.completed) == sorted(fi.alias for fi in file_infos)
    assert client.max_open == 3


async def test_box_full_of_other_uploads_stops_the_pass(tmp_path: Path):
    """With the box full of uploads that are not the batch's, the pass stops and
    says how to free the box, since nothing in the batch can free it.
    """
    file_infos = make_files_in_flight(tmp_path, {"one": 2, "two": 1})
    others = tuple(f"stale-{i}" for i in range(5))
    client = RecordingUploadClient(open_limit=5, others_open=others)

    with patch(
        "ghga_connector.core.uploading.batch_processing.CLIMessageDisplay"
    ) as display:
        result = await upload_in_flight(client, file_infos, parts=4, files=2)

    assert result.halted
    assert [fi.alias for fi in result.failed] == ["one", "two"]
    assert client.created == []
    [message] = [call.args[0] for call in display.failure.call_args_list]
    assert "ghga-connector ubox" in message


async def test_other_429_keeps_its_retries(tmp_path: Path):
    """A 429 that is not about open uploads is retried as before."""
    file_infos = make_files_in_flight(tmp_path, {"one": 2, "two": 1})
    client = RecordingUploadClient(busy_once=("one",))

    with patch("ghga_connector.core.uploading.uploader.UPLOAD_RETRY_BACKOFF_SEC", 0):
        result = await upload_in_flight(client, file_infos, parts=4, files=2)

    assert result == BatchPassResult()
    assert sorted(client.completed) == ["one", "two"]


async def test_last_file_takes_the_part_slots_the_others_free(tmp_path: Path):
    """Once the small files of a batch end, the large file left sends as many parts
    as the budget allows, not only the share it started with.
    """
    file_infos = make_files_in_flight(
        tmp_path, {"large": 24, "small-1": 1, "small-2": 1, "small-3": 1}
    )
    client = RecordingUploadClient()

    await upload_in_flight(client, file_infos, parts=10, files=4)

    assert client.max_per_file == 10


async def test_box_full_of_other_uploads_in_the_shell_advises_rm(tmp_path: Path):
    """In the ubox shell, the halt advises the shell's `rm`, not the commands of the
    command line.
    """
    file_infos = make_files_in_flight(tmp_path, {"one": 1})
    others = tuple(f"stale-{i}" for i in range(5))
    client = RecordingUploadClient(open_limit=5, others_open=others)

    with patch(
        "ghga_connector.core.uploading.batch_processing.CLIMessageDisplay"
    ) as display:
        result = await upload_in_flight(
            client, file_infos, parts=4, files=1, in_shell=True
        )

    assert result.halted
    [message] = [call.args[0] for call in display.failure.call_args_list]
    assert "`rm ALIAS`" in message
    assert "--overwrite" not in message
    assert "ghga-connector ubox" not in message


def _wait_notices(display: MagicMock) -> list[str]:
    """Return the messages that told the user a file waits for room in the box."""
    messages = [str(call.args[0]) for call in display.display.call_args_list]
    return [message for message in messages if "waits for another file" in message]


async def test_creates_refused_together_halt_without_wait_notices(tmp_path: Path):
    """When every create of the batch is refused for the open-upload limit, the pass
    halts without first telling the user that files wait.
    """
    file_infos = make_files_in_flight(tmp_path, {f"file-{i}": 1 for i in range(4)})
    others = tuple(f"stale-{i}" for i in range(5))
    client = RecordingUploadClient(
        open_limit=5, others_open=others, create_seconds=0.01
    )

    with patch(
        "ghga_connector.core.uploading.batch_processing.CLIMessageDisplay"
    ) as display:
        result = await upload_in_flight(client, file_infos, parts=10, files=4)

    assert result.halted
    assert _wait_notices(display) == []


async def test_files_waiting_for_an_upload_of_the_batch_are_announced(tmp_path: Path):
    """A file that waits for a file of the batch to end is announced once."""
    file_infos = make_files_in_flight(tmp_path, {f"file-{i}": 1 for i in range(4)})
    others = ("stale-0", "stale-1", "stale-2")
    client = RecordingUploadClient(
        open_limit=5, others_open=others, create_seconds=0.01
    )

    with patch(
        "ghga_connector.core.uploading.batch_processing.CLIMessageDisplay"
    ) as display:
        result = await upload_in_flight(client, file_infos, parts=10, files=4)

    assert result == BatchPassResult()
    notices = _wait_notices(display)
    assert notices
    assert len(notices) == len(set(notices))


async def test_creates_go_one_at_a_time(tmp_path: Path):
    """UCS checks the box's limits before it records an upload, so creates sent
    together would all pass: the batch sends one at a time.
    """
    file_infos = make_files_in_flight(tmp_path, {f"file-{i}": 1 for i in range(4)})
    client = RecordingUploadClient(create_seconds=0.05)

    result = await upload_in_flight(client, file_infos, parts=10, files=4)

    assert result == BatchPassResult()
    assert len(client.created) == 4
    assert client.max_creating == 1
