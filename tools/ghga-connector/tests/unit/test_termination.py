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
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer
from pydantic import SecretBytes

from ghga_connector import cli
from ghga_connector.cli import _catch_cancellations
from ghga_connector.core import main
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
async def test_an_ignored_signal_stays_ignored():
    """Under nohup SIGHUP is ignored, so the command goes on when the terminal closes."""

    async def hang_up_then_finish() -> None:
        os.kill(os.getpid(), signal.SIGHUP)
        await asyncio.sleep(0.05)

    previous = signal.signal(signal.SIGHUP, signal.SIG_IGN)
    try:
        with patch("ghga_connector.core.termination._discard_output"):
            await cancel_on_termination(hang_up_then_finish())
        assert not termination_requested()
        assert signal.getsignal(signal.SIGHUP) == signal.SIG_IGN
    finally:
        signal.signal(signal.SIGHUP, previous)


@pytest.mark.asyncio
async def test_a_cancellation_the_command_handled_is_passed_on():
    """Ctrl+C cancels the command, which cleans up and returns; the cancellation is
    then passed on, so the CLI reports the abort and exits with 130.
    """

    async def clean_up_and_return() -> None:
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            return

    task = asyncio.ensure_future(cancel_on_termination(clean_up_and_return()))
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def _open_output(kind: str, tmp_path: Path) -> list[int]:
    """Open an output of the given kind and return its file descriptors, the one to
    write to first.
    """
    if kind == "file":
        return [os.open(tmp_path / "out.log", os.O_WRONLY | os.O_CREAT)]
    if kind == "pipe":
        read_end, write_end = os.pipe()
        return [write_end, read_end]
    controller, terminal = os.openpty()
    return [terminal, controller]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind, discarded", [("file", False), ("pipe", True), ("terminal", True)]
)
async def test_sighup_discards_output_whose_reader_hangs_up(
    kind: str, discarded: bool, tmp_path: Path
):
    """After SIGHUP, output to the terminal is discarded, and so is output to a pipe,
    e.g. to `tee`, whose reader gets the same hangup. Output to a file is kept.
    """
    fds = _open_output(kind, tmp_path)
    stdout = os.dup(1)
    os.dup2(fds[0], 1)
    try:
        with (
            patch("ghga_connector.core.termination._discard_output") as discard_output,
            pytest.raises(TerminatedError),
        ):
            await cancel_on_termination(_signal_then_clean_up(signal.SIGHUP, []))
    finally:
        os.dup2(stdout, 1)
        for fd in [stdout, *fds]:
            os.close(fd)

    assert (1 in discard_output.call_args.args[0]) == discarded


@pytest.mark.parametrize("command", ["batch-upload", "ubox"])
def test_prompts_keep_the_default_sigterm_action(
    command: str, monkeypatch: pytest.MonkeyPatch
):
    """The passphrase and access token prompts block the event loop, which could not
    run a signal handler meanwhile, so they keep the default SIGTERM action. Only the
    upload or the shell after them handles SIGTERM.
    """
    default_action = signal.getsignal(signal.SIGTERM)
    actions: dict[str, object] = {}

    def record(step: str):
        def recording_step(*_args, **_kwargs):
            actions[step] = signal.getsignal(signal.SIGTERM)
            return MagicMock()

        return recording_step

    @asynccontextmanager
    async def no_client(*_args, **_kwargs):
        yield MagicMock()

    async def upload(**_kwargs) -> None:
        actions["upload"] = signal.getsignal(signal.SIGTERM)

    class Shell:
        def __init__(self, **_kwargs):
            pass

        async def run(self) -> None:
            await upload()

    monkeypatch.setattr(main, "async_client", no_client)
    monkeypatch.setattr(main, "set_runtime_config", no_client)
    monkeypatch.setattr(main, "load_file_info_from_tsv", lambda _tsv: [])
    monkeypatch.setattr(main.utils, "get_public_key", lambda _path: b"")
    monkeypatch.setattr(main.utils, "get_private_key", record("passphrase"))
    monkeypatch.setattr(main, "WorkPackageClient", record("token"))
    monkeypatch.setattr(main, "UploadClient", MagicMock())
    monkeypatch.setattr(main, "run_batch_upload", upload)
    monkeypatch.setattr(main, "UboxShell", Shell)

    keys = {"my_public_key_path": Path("key.pub"), "my_private_key_path": Path("key")}
    if command == "batch-upload":
        cli.batch_upload(
            tsv=Path("files.tsv"),
            max_retries=0,
            dry_run=False,
            shorten_names=False,
            overwrite=False,
            debug=False,
            **keys,
        )
    else:
        cli.ubox(debug=False, **keys)

    assert actions["passphrase"] == default_action
    assert actions["token"] == default_action
    assert actions["upload"] != default_action


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
