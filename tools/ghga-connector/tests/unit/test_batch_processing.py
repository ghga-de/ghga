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

import signal
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from pydantic import SecretBytes

from ghga_connector import exceptions
from ghga_connector.constants import BATCH_RETRY_BACKOFF_SEC
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
from ghga_connector.core.uploading.structs import UploadedFileInfo
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
            [UploadedFileInfo(id=uuid4(), alias="already", state="interrogated")]
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
                UploadedFileInfo(id=uuid4(), alias="cancelled-file", state="cancelled"),
                UploadedFileInfo(id=uuid4(), alias="failed-file", state="failed"),
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


async def test_run_batch_upload_all_skipped_does_not_upload():
    """When every file is already uploaded, no upload pass is attempted."""
    with NamedTemporaryFile() as f:
        file_infos = [make_file_info_for_upload(path=Path(f.name), alias="done")]
        upload_client = _make_upload_client(
            [UploadedFileInfo(id=uuid4(), alias="done", state="interrogated")]
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
            [UploadedFileInfo(id=uuid4(), alias="already", state="interrogated")]
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
        UploadedFileInfo(id=uuid4(), alias=f"file-{i}", state="interrogated")
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
