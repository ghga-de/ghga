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

"""Stop a command on SIGTERM or SIGHUP the way Ctrl+C does, cleanup included.

Without this, both signals end the process at once and leave an unfinished upload
in the box, where it counts against the box's limit of open uploads until UCS
removes it days later.
"""

import asyncio
import os
import signal
import stat
from collections.abc import Coroutine
from dataclasses import dataclass
from typing import Any

TERMINATION_SIGNALS = (signal.SIGTERM, signal.SIGHUP)


@dataclass
class _Received:
    """The termination signal received during the current command, if any."""

    signum: signal.Signals | None = None


_received = _Received()


class TerminatedError(Exception):
    """Raised once a command cancelled by SIGTERM or SIGHUP has ended."""

    def __init__(self, signum: signal.Signals):
        self.signum = signum
        super().__init__(f"The operation was stopped by {signum.name}.")


def termination_requested() -> bool:
    """Return True once SIGTERM or SIGHUP was received during the current command."""
    return _received.signum is not None


def _discard_output(fds: list[int]) -> None:
    """Point the given ones of stdout and stderr at /dev/null.

    After SIGHUP the terminal is usually gone, and a write to it raises an OSError
    that would break off the cleanup. Output redirected to a file or pipe stays.
    """
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        for fd in fds:
            os.dup2(devnull, fd)
    finally:
        os.close(devnull)


def _gone_on_hangup(fd: int) -> bool:
    """Whether output to `fd` likely fails once the terminal hangs up.

    Besides the terminal itself that is a pipe, e.g. to `tee`, whose reader gets the
    same SIGHUP. A file keeps the output.
    """
    try:
        mode = os.fstat(fd).st_mode
    except OSError:
        return False
    return os.isatty(fd) or stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode)


async def cancel_on_termination(coroutine: Coroutine[Any, Any, Any]) -> None:
    """Await `coroutine`, cancelling it on SIGTERM or SIGHUP as asyncio does on Ctrl+C.

    The cancellation runs the same cleanup as Ctrl+C. Further termination signals
    are ignored, so they cannot interrupt that cleanup. Raises `TerminatedError`
    once `coroutine` has ended after such a signal.
    """
    _received.signum = None
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    # Checked now, since a terminal that hung up may no longer report as one
    terminal_fds = [fd for fd in (1, 2) if _gone_on_hangup(fd)]

    def on_signal(signum: signal.Signals) -> None:
        if _received.signum is not None or task is None:
            return
        _received.signum = signum
        if signum == signal.SIGHUP:
            _discard_output(terminal_fds)
        task.cancel()

    # A signal that is ignored, e.g. SIGHUP under nohup, stays ignored
    handled = [
        signum
        for signum in TERMINATION_SIGNALS
        if signal.getsignal(signum) is not signal.SIG_IGN
    ]
    for signum in handled:
        loop.add_signal_handler(signum, on_signal, signum)
    try:
        await coroutine
    except asyncio.CancelledError:
        if _received.signum is None:
            raise
    finally:
        for signum in handled:
            loop.remove_signal_handler(signum)
    if _received.signum is not None:
        raise TerminatedError(_received.signum)
    if task is not None and task.cancelling():
        # Ctrl+C cancelled the command, which cleaned up and returned: let asyncio
        #  report it as KeyboardInterrupt, so the CLI exits with 130
        raise asyncio.CancelledError
