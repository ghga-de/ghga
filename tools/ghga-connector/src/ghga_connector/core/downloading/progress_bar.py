# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)


class ProgressBar:
    """Download progress bar wrapping rich behavior. To be used as context manager."""

    def __init__(self, file_name: str, file_size: int, binary_units: bool = False):
        self._task_id = TaskID(-1)
        self._file_name = file_name
        self._file_size = file_size

        self._progress = Progress(
            TextColumn(f"Downloading to file '{self._file_name}'"),
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
            description="File Download",
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
