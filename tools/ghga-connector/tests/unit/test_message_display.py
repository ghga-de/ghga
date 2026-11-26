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

"""Tests for the CLI message display"""

import io
import sys

import pytest
from rich.console import Console
from rich.file_proxy import FileProxy

from ghga_connector.core.message_display import CLIMessageDisplay


class Terminal(io.StringIO):
    """A text stream that reports to be a terminal."""

    def isatty(self) -> bool:
        """Claim to be a terminal."""
        return True


@pytest.mark.parametrize(
    "stream_name, write",
    [("stdout", CLIMessageDisplay.success), ("stderr", CLIMessageDisplay.failure)],
)
def test_messages_print_above_a_live_display(monkeypatch, stream_name, write):
    """While a live display has swapped the stream for its proxy, a message goes
    through the proxy, which prints it above the display, and keeps its color.
    """
    printed = io.StringIO()
    console = Console(file=printed, force_terminal=True, color_system="standard")
    monkeypatch.setattr(sys, stream_name, FileProxy(console, Terminal()))

    write("Uploaded the file.")

    assert "Uploaded the file." in printed.getvalue()
    assert "\x1b[3" in printed.getvalue()  # a foreground color


def test_messages_have_no_color_off_a_terminal(capsys):
    """A message to a stream that is no terminal carries no color codes."""
    CLIMessageDisplay.success("Uploaded the file.")
    assert capsys.readouterr().out == "Uploaded the file.\n"


def test_messages_reach_a_redirected_stream_during_a_live_display(monkeypatch):
    """With stderr redirected, e.g. to a log file, a failure goes to that file, not
    through the live display's proxy to the terminal.
    """
    printed = io.StringIO()
    console = Console(file=printed, force_terminal=True, color_system="standard")
    log_file = io.StringIO()
    monkeypatch.setattr(sys, "stderr", FileProxy(console, log_file))

    CLIMessageDisplay.failure("Failed to upload the file.")

    assert log_file.getvalue() == "Failed to upload the file.\n"
    assert "Failed to upload the file." not in printed.getvalue()


class BrokenPipe(io.StringIO):
    """A stream whose reader is gone, such as a pipe to `tee` after a hangup."""

    def write(self, text: str) -> int:
        """Fail as a pipe without a reader does."""
        raise BrokenPipeError(32, "Broken pipe")


def test_a_message_that_cannot_be_written_is_dropped(monkeypatch):
    """A message to a stream that fails is dropped, so it cannot cut off the cleanup
    that follows it.
    """
    monkeypatch.setattr(sys, "stderr", BrokenPipe())

    CLIMessageDisplay.failure("Upload aborted for a, deleting.")
