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
"""Contains progress bar related code for a better user experience"""

from types import TracebackType
from typing import Literal

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    Task,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)


class _ProgressBar:
    """Progress bar wrapping rich behavior. To be used as context manager."""

    activity: Literal["Download", "Upload"]

    def __init__(self, file_name: str, file_size: int, binary_units: bool = False):
        self._task_id = TaskID(-1)
        self._file_name = file_name
        self._file_size = file_size

        self._progress = Progress(
            TextColumn(f"{self.activity}ing file '{self._file_name}'"),
            BarColumn(),
            TimeRemainingColumn(compact=True, elapsed_when_finished=True),
            TransferSpeedColumn(),
            DownloadColumn(binary_units=binary_units),
            auto_refresh=False,
        )

    def __enter__(self):
        """Enable progress bar and add progress bar task on enter."""
        self._progress.start()
        self._task_id = self._progress.add_task(
            description=f"File {self.activity}",
            total=self._file_size,
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Remove existing task on failure and stop progress bar."""
        if exc_type:
            self._progress.remove_task(self._task_id)
        self._progress.stop()
        # add a newline so next output is alway printed on a separate line
        print()

    def advance(self, size: int):
        """Advance progress bar by specified amount of bytes and display."""
        # Abort if no task exists
        if self._task_id < 0:
            raise ValueError("ProgressBar has to be used as a context manager.")

        self._progress.update(self._task_id, advance=size)
        # clamp progress bar to 100%
        if self._progress.tasks[self._task_id].completed > self._file_size:  # noqa: PLR1730
            self._progress.tasks[self._task_id].completed = self._file_size
        self._progress.refresh()


class DownloadProgressBar(_ProgressBar):
    """A progress bar for file downloads. To be used as context manager."""

    activity = "Download"


class UploadProgressBar(_ProgressBar):
    """A progress bar for file uploads. To be used as context manager."""

    activity = "Upload"


def _upload_columns(binary_units: bool) -> list:
    """The columns of an upload row: name, bar, time, speed and amount."""
    return [
        TextColumn("{task.description}"),
        BarColumn(),
        TimeRemainingColumn(compact=True, elapsed_when_finished=True),
        TransferSpeedColumn(),
        DownloadColumn(binary_units=binary_units),
    ]


class BatchUploadProgress:
    """One live progress display for a batch upload, with a row per file in flight.

    rich allows one live display at a time, so the files of a batch share this one.
    To be used as context manager around the batch; `file_row` gives each file its row.
    """

    def __init__(self, binary_units: bool = False):
        self._progress = Progress(*_upload_columns(binary_units), auto_refresh=False)

    def __enter__(self):
        """Start the live display."""
        self._progress.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Stop the live display."""
        self._progress.stop()
        # add a newline so next output is always printed on a separate line
        print()

    def file_row(self, file_name: str, file_size: int) -> "FileProgressRow":
        """Return the row for one file, to be entered when its upload starts."""
        return FileProgressRow(self._progress, file_name=file_name, file_size=file_size)


class FileProgressRow:
    """A file's row in a `BatchUploadProgress`. To be used as context manager.

    The row leaves the display when the upload ends, finished or failed, so the display
    shows only the files in flight; the batch's messages say how each file ended.
    """

    def __init__(self, progress: Progress, *, file_name: str, file_size: int):
        self._progress = progress
        self._file_name = file_name
        self._file_size = file_size
        self._task_id = TaskID(-1)

    def __enter__(self):
        """Add the file's row to the display."""
        self._task_id = self._progress.add_task(
            description=f"Uploading file '{self._file_name}'", total=self._file_size
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ):
        """Take the row out of the display."""
        self._progress.remove_task(self._task_id)
        self._progress.refresh()

    def advance(self, size: int):
        """Advance the row by the given number of bytes and refresh the display."""
        if self._task_id < 0:
            raise ValueError("FileProgressRow has to be used as a context manager.")
        self._progress.update(self._task_id, advance=size)
        # clamp progress bar to 100%
        if self._task().completed > self._file_size:
            self._progress.update(self._task_id, completed=self._file_size)
        self._progress.refresh()

    def _task(self) -> Task:
        """Return the row's task; the display's task list holds other files' too."""
        return next(task for task in self._progress.tasks if task.id == self._task_id)
