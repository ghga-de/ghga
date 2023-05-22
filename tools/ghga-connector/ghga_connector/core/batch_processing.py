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

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from time import sleep

from ghga_connector.core import exceptions
from ghga_connector.core.api_calls import (
    WorkPackageAccessor,
    check_url,
    get_download_url,
)
from ghga_connector.core.message_display import AbstractMessageDisplay


class InputHandler(ABC):
    """Abstract base for dealing with user input in batch processing"""

    @abstractmethod
    def get_input(self, *, message: str):
        """Handle user input."""

    @abstractmethod
    def handle_response(self, *, response: str):
        """Handle response from get_input."""


class OutputHandler(ABC):
    """Abstract base for checking existing content in a provided output location."""

    @abstractmethod
    def check_output(self, *, location: Path) -> list[str]:
        """Check for and return existing files in output location."""


@dataclass
class BatchIoHandler(ABC):
    """Convenience class to hold both input and output handlers"""

    input_handler: InputHandler
    output_handler: OutputHandler

    @abstractmethod
    def check_output(self, *, location: Path) -> list[str]:
        """Check for and return existing files in output location."""

    @abstractmethod
    def get_input(self, *, message: str):
        """User input handling."""

    @abstractmethod
    def handle_response(self, *, response: str):
        """Handle response from get_input."""


class CliInputHandler(InputHandler):
    """CLI relevant input handling"""

    def get_input(self, *, message: str):
        """Simple user input handling."""
        return input(message)

    def handle_response(self, *, response: str):
        """Handle response from get_input."""
        if not response.lower() == "yes":
            raise exceptions.AbortBatchProcessError()


@dataclass
class LocalOutputHandler(OutputHandler):
    """Implements checks for an output directory on the local file system."""

    file_ids_with_extension: dict[str, str] = field(default_factory=dict, init=False)

    def check_output(self, *, location: Path) -> list[str]:
        """Check for and return existing files in output directory."""
        existing_files = []

        # check local files with and without extension
        for file_id, file_extension in self.file_ids_with_extension.items():
            if file_extension:
                file = location / f"{file_id}{file_extension}.c4gh"
            else:
                file = location / f"{file_id}.c4gh"

            if file.exists():
                existing_files.append(file_id)

        return existing_files


@dataclass
class CliIoHandler(BatchIoHandler):
    """Convenience class to hold both input and output handlers"""

    input_handler: CliInputHandler = field(default_factory=CliInputHandler, init=False)
    output_handler: LocalOutputHandler = field(
        default_factory=LocalOutputHandler, init=False
    )

    def check_output(self, *, location: Path) -> list[str]:
        """Check for and return existing files that would in output directory."""
        return self.output_handler.check_output(location=location)

    def get_input(self, *, message: str):
        """Simple user input handling."""
        return self.input_handler.get_input(message=message)

    def handle_response(self, *, response: str):
        """Handle response from get_input."""
        return self.input_handler.handle_response(response=response)


class StagingParameters:
    """Container for variable parameters provided to the batch processor"""

    def __init__(
        self,
        api_url: str,
        file_ids_with_extension: dict[str, str],
        max_wait_time: int,
        retry_after: int = 60,
    ) -> None:
        self.api_url = api_url
        self.check_api_available()
        self.file_ids_with_extension = file_ids_with_extension
        self.max_wait_time = max_wait_time
        # amount of seconds between staging attempts
        self.retry_after = retry_after

    def check_api_available(self):
        """Get response from endpoint, else throw corresponding exception"""
        if not check_url(self.api_url):
            raise exceptions.ApiNotReachableError(api_url=self.api_url)

    def get_file_ids(self) -> list[str]:
        """Get file ids that should be staged"""
        return list(self.file_ids_with_extension.keys())

    def remove_existing(self, *, file_ids: list[str]):
        """Delete file information for already existing files."""
        for file_id in file_ids:
            del self.file_ids_with_extension[file_id]


@dataclass
class StagingState:
    """Handle state for staged and not yet staged file ids."""

    time_started: datetime = field(default_factory=datetime.utcnow, init=False)
    staged_files: list[str] = field(default_factory=list, init=False)
    unstaged_files: list[str] = field(default_factory=list, init=False)

    def add_staged(self, *, file_id: str):
        """Delegate adding staged file ids"""
        self.staged_files.append(file_id)

    def add_unstaged(self, *, file_id: str):
        """Delegate adding unstaged file ids"""
        self.unstaged_files.append(file_id)

    def update_staged_files_wait(
        self, *, max_wait_time: int, work_package_accessor: WorkPackageAccessor
    ) -> bool:
        """
        Update staged file list after all previously staged files have been processed.
        Caller has to make sure, that all file ids in self.staged_files have actually
        been processed.

        Returns a boolean instructing the caller to wait for retry_time and call this
        method again.
        """
        self.staged_files = []
        remaining_unstaged = []

        for file_id in self.unstaged_files:
            dl_url = get_download_url(
                file_id=file_id, work_package_accessor=work_package_accessor
            )
            if dl_url[0]:
                self.staged_files.append(file_id)
            else:
                remaining_unstaged.append(file_id)

        self.unstaged_files = remaining_unstaged

        if self.unstaged_files and not self.staged_files:
            self._check_wait_time(max_wait_time=max_wait_time)
            return True
        return False

    def _check_wait_time(self, *, max_wait_time: int):
        """Raise exception if maximum wait time has been exceeded"""

        time_waited = datetime.utcnow() - self.time_started
        if time_waited.total_seconds() >= max_wait_time:
            raise exceptions.MaxWaitTimeExceededError(max_wait_time=max_wait_time)


@dataclass
class FileStager:  # pylint: disable=too-many-instance-attributes
    """Utility class to deal with file staging in batch processing."""

    message_display: AbstractMessageDisplay
    io_handler: BatchIoHandler
    staging_parameters: StagingParameters
    staging_state: StagingState = field(default_factory=StagingState, init=False)
    work_package_accessor: WorkPackageAccessor

    def check_and_stage(self, output_dir: Path):
        """Call DRS endpoint to stage files. Report file ids with 404 responses to user."""

        existing_files = self.io_handler.check_output(location=output_dir)
        self.staging_parameters.remove_existing(file_ids=existing_files)

        unknown_ids = []
        for file_id in self.staging_parameters.file_ids_with_extension.keys():
            try:
                download_information = get_download_url(
                    file_id=file_id, work_package_accessor=self.work_package_accessor
                )
            except exceptions.BadResponseCodeError as error:
                if error.response_code == 404:
                    unknown_ids.append(file_id)
                    continue
                raise error

            # split into already staged and not yet staged files
            if download_information[0]:
                self.staging_state.add_staged(file_id=file_id)
            else:
                self.staging_state.add_unstaged(file_id=file_id)

        if unknown_ids:
            self._handle_unknown(unknown_ids)

    def file_ids_remain(self):
        """Returns if any staged or unstaged file ids remain"""
        return any((self.staging_state.staged_files, self.staging_state.unstaged_files))

    def get_staged(self):
        """Return currently staged file ids"""
        return self.staging_state.staged_files

    def update_staged_files(self):
        """Delegate updating file_ids for staging and handle wait/retries."""
        while self.staging_state.update_staged_files_wait(
            max_wait_time=self.staging_parameters.max_wait_time,
            work_package_accessor=self.work_package_accessor,
        ):
            self.message_display.display(
                f"No staged files available, retrying in {self.staging_parameters.retry_after}"
                + f" seconds for {len(self.staging_state.unstaged_files)} unstaged file(s)."
            )
            sleep(self.staging_parameters.retry_after)

    def _handle_unknown(self, unknown_ids: list[str]):
        """Process user interaction for unknown file IDs"""
        message = (
            f"No download exists for the following file IDs: {' ,'.join(unknown_ids)}"
        )
        self.message_display.failure(message)

        unknown_ids_present = (
            "Some of the provided file IDs cannot be downloaded."
            + "\nDo you want to proceed ?\n[Yes][No]\n"
        )
        response = self.io_handler.get_input(message=unknown_ids_present)
        self.io_handler.handle_response(response=response)
        self.message_display.display("Downloading remaining files")
