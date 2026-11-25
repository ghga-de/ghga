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

"""Unit tests for stopping a command on SIGTERM or SIGHUP"""

import asyncio
import os
import signal
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import AsyncMock, patch

import pytest
import typer
from pydantic import SecretBytes

from ghga_connector.cli import _catch_cancellations
from ghga_connector.core.termination import (
    TerminatedError,
    cancel_on_termination,
    termination_requested,
)
from ghga_connector.core.uploading.batch_processing import upload_files_from_list
from tests.fixtures.utils import make_file_info_for_upload
from tests.unit.test_batch_processing import make_mock_uploader


async def _signal_then_clean_up(signum: signal.Signals, steps: list[str]) -> None:
    """Send `signum` to this process, then clean up as the upload code does on Ctrl+C.

    A second SIGTERM is sent during the cleanup, which must not interrupt it.
    """
    try:
        os.kill(os.getpid(), signum)
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        steps.append("cancelled")
        os.kill(os.getpid(), signal.SIGTERM)
        await asyncio.sleep(0.05)
        steps.append("cleaned up")


@pytest.mark.asyncio
@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGHUP])
async def test_termination_signal_cancels_and_lets_cleanup_finish(
    signum: signal.Signals,
):
    """A termination signal cancels the command, whose cleanup then runs to the end."""
    steps: list[str] = []
    with (
        patch("ghga_connector.core.termination._discard_output") as discard_output,
        pytest.raises(TerminatedError) as exc_info,
    ):
        await cancel_on_termination(_signal_then_clean_up(signum, steps))

    assert exc_info.value.signum == signum
    assert steps == ["cancelled", "cleaned up"]
    assert termination_requested()
    # Only SIGHUP means the terminal is gone
    assert discard_output.called == (signum == signal.SIGHUP)


@pytest.mark.asyncio
async def test_no_signal_returns_normally():
    """Without a termination signal, the command ends normally and the handlers go."""
    await cancel_on_termination(asyncio.sleep(0))

    assert not termination_requested()
    assert signal.getsignal(signal.SIGTERM) == signal.SIG_DFL


@pytest.mark.asyncio
async def test_other_cancellation_propagates():
    """A cancellation without a termination signal, as on Ctrl+C, is passed on."""

    async def cancelled() -> None:
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await cancel_on_termination(cancelled())


@pytest.mark.asyncio
async def test_sigterm_deletes_the_open_upload():
    """SIGTERM during an upload deletes the unfinished upload, as Ctrl+C does."""

    async def upload_until_terminated(**_kwargs) -> None:
        os.kill(os.getpid(), signal.SIGTERM)
        await asyncio.sleep(10)

    uploader = make_mock_uploader()
    uploader.upload_file.side_effect = upload_until_terminated
    with NamedTemporaryFile() as f:
        file_infos = [make_file_info_for_upload(path=Path(f.name), alias="big-file")]
        with (
            patch(
                "ghga_connector.core.uploading.batch_processing.Uploader",
                return_value=uploader,
            ),
            patch("ghga_connector.core.uploading.batch_processing.Crypt4GHEncryptor"),
            pytest.raises(TerminatedError),
        ):
            await cancel_on_termination(
                upload_files_from_list(
                    upload_client=AsyncMock(),
                    file_info_list=file_infos,
                    my_private_key=SecretBytes(b"\x00" * 32),
                    max_concurrent_uploads=1,
                )
            )

    uploader.delete_file.assert_awaited_once()


@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGHUP])
def test_cli_exits_with_the_signal_exit_code(signum: signal.Signals):
    """The CLI exits with the code a shell reports for the termination signal."""

    async def terminated() -> None:
        raise TerminatedError(signum)

    with pytest.raises(typer.Exit) as exc_info:
        _catch_cancellations(terminated())

    assert exc_info.value.exit_code == 128 + signum
