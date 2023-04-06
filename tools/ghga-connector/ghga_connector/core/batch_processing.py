# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""Module for btach processing specific code"""

from dataclasses import dataclass, field
from datetime import datetime
from time import sleep

from ghga_connector.core import exceptions
from ghga_connector.core.api_calls import check_url, get_download_url
from ghga_connector.core.message_display import AbstractMessageDisplay


@dataclass
class FileStager:
    """Utility class to deal with file staging in batch processing."""

    api_url: str
    message_display: AbstractMessageDisplay
    max_wait_time: int
    # amount of seconds between staging attempts
    retry_after: int = field(default=120)

    time_started: datetime = field(default_factory=datetime.utcnow, init=False)
    staged_files: list[str] = field(default_factory=list, init=False)
    unstaged_files: list[str] = field(default_factory=list, init=False)

    def check_and_stage(self, file_ids: list[str]):
        """Call DRS endpoint to stage files. Report file ids with 404 responses to user."""

        # verify the API is actually reachable
        if not check_url(self.api_url):
            self.message_display.failure(
                f"The url {self.api_url} is currently not reachable."
            )
            raise exceptions.ApiNotReachableError(api_url=self.api_url)

        unknown_ids = []
        for file_id in file_ids:
            try:
                download_information = get_download_url(
                    api_url=self.api_url, file_id=file_id
                )
            except exceptions.BadResponseCodeError as error:
                if error.response_code == 404:
                    unknown_ids.append(file_id)
                    continue
                raise error

            # split into already staged and not yet staged files
            if download_information[0]:
                self.staged_files.append(file_id)
            else:
                self.unstaged_files.append(file_id)

        if unknown_ids:
            self._handle_unknown(unknown_ids)

    def update_staged_files(self):
        """
        Update staged file list after all previously staged files have been processed.
        Caller has to make sure, that all file ids in self.staged_files have actually
        been processed
        """
        self.staged_files = []
        remaining_unstaged = []

        for file_id in self.unstaged_files:
            dl_url = get_download_url(api_url=self.api_url, file_id=file_id)
            if dl_url[0]:
                self.staged_files.append(file_id)
            else:
                remaining_unstaged.append(file_id)

        self.unstaged_files = remaining_unstaged

        if self.unstaged_files and not self.staged_files:
            time_waited = datetime.utcnow() - self.time_started
            if time_waited.total_seconds() >= self.max_wait_time:
                raise exceptions.MaxWaitTimeExceededError(
                    max_wait_time=self.max_wait_time
                )
            self.message_display.display(
                f"No staged files available, retrying in {self.retry_after} seconds for "
                + f"{len(self.unstaged_files)} unstaged file(s)."
            )
            sleep(self.retry_after)

    def _handle_unknown(self, unknown_ids: list[str]):
        """Process user interaction for unknown file IDs"""
        message = (
            f"No download exists for the following file IDs: {' ,'.join(unknown_ids)}"
        )
        self.message_display.failure(message)
        response = _get_input()
        if not response.lower() == "yes":
            self.message_display.display("Aborting batch process")
            # would directly calling sys.exit be better here?
            self.staged_files = self.unstaged_files = []
        else:
            self.message_display.display("Downloading remaining files")


def _get_input():
    """User input handling. Factored out to be patchable in tests."""
    message = (
        "Some of the provided file IDs cannot be downloaded."
        + "\nDo you want to proceed ?\n[Yes][No]\t"
    )
    return input(message)
