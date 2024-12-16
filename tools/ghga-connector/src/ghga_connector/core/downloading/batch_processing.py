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
"""Module for batch processing related code"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter, sleep

import httpx

from ghga_connector.config import Config
from ghga_connector.core import (
    AbstractMessageDisplay,
    WorkPackageAccessor,
    exceptions,
)
from ghga_connector.core.api_calls import is_service_healthy

from .api_calls import (
    get_download_url,
    get_file_authorization,
)
from .structs import RetryResponse, URLResponse


class InputHandler(ABC):
    """Abstract base for dealing with user input in batch processing"""

    @abstractmethod
    def get_input(self, *, message: str) -> str:
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
    def get_input(self, *, message: str) -> str:
        """User input handling."""

    @abstractmethod
    def handle_response(self, *, response: str):
        """Handle response from get_input."""


class CliInputHandler(InputHandler):
    """CLI relevant input handling"""

    def get_input(self, *, message: str) -> str:
        """Simple user input handling."""
        return input(message)

    def handle_response(self, *, response: str):
        """Handle response from get_input."""
        if not (response.lower() == "yes" or response.lower() == "y"):
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

    def get_input(self, *, message: str) -> str:
        """Simple user input handling."""
        return self.input_handler.get_input(message=message)

    def handle_response(self, *, response: str):
        """Handle response from get_input."""
        return self.input_handler.handle_response(response=response)


class FileStager:
    """Utility class to deal with file staging in batch processing."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        wanted_file_ids: list[str],
        dcs_api_url: str,
        output_dir: Path,
        message_display: AbstractMessageDisplay,
        work_package_accessor: WorkPackageAccessor,
        client: httpx.AsyncClient,
        config: Config,
    ):
        """Initialize the FileStager."""
        self.io_handler = CliIoHandler()
        existing_file_ids = set(self.io_handler.check_output(location=output_dir))
        if not is_service_healthy(dcs_api_url):
            raise exceptions.ApiNotReachableError(api_url=dcs_api_url)
        self.api_url = dcs_api_url
        self.message_display = message_display
        self.work_package_accessor = work_package_accessor
        self.max_wait_time = config.max_wait_time
        self.client = client
        self.started_waiting = now = perf_counter()

        # Successfully staged files with their download URLs and sizes
        # in the beginning, consider all files as staged with a retry time of 0
        self.staged_urls: dict[str, URLResponse] = {}
        # Files that are currently being staged with retry times:
        self.unstaged_retry_times = {
            file_id: now
            for file_id in wanted_file_ids
            if file_id not in existing_file_ids
        }
        # Files that could not be staged because they cannot be found:
        self.missing_files: list[str] = []
        self.ignore_failed = False

    async def get_staged_files(self) -> dict[str, URLResponse]:
        """Get files that are already staged.

        Returns a dict with file IDs as keys and URLResponses as values.
        These values contain the download URLs and file sizes.
        The dict should cleared after these files have been downloaded.
        """
        self.message_display.display("Updating list of staged files...")
        staging_items = list(self.unstaged_retry_times.items())
        for file_id, retry_time in staging_items:
            if perf_counter() >= retry_time:
                await self._check_file(file_id=file_id)
            if len(self.staged_urls.items()) > 0:
                self.started_waiting = perf_counter()  # reset wait timer
                break
        if not self.staged_urls and not self._handle_failures():
            sleep(1)
        self._check_timeout()
        return self.staged_urls

    @property
    def finished(self) -> bool:
        """Check whether work is finished, i.e. no staged or unstaged files remain."""
        return not (self.staged_urls or self.unstaged_retry_times)

    async def _check_file(self, file_id: str) -> None:
        """Check whether a file with the given file_id is staged.

        The method returns nothing, but adapts the internal state accordingly.
        Particularly, files that cannot be found are added to missing_files.
        If files cannot be staged for other reason, a BadResponseCodeError is raised.
        """
        try:
            url_and_headers = await get_file_authorization(
                file_id=file_id,
                work_package_accessor=self.work_package_accessor,
            )
            response = await get_download_url(
                client=self.client, url_and_headers=url_and_headers
            )

        except exceptions.BadResponseCodeError as error:
            if error.response_code != 404:
                raise
            response = None
        if isinstance(response, URLResponse):
            del self.unstaged_retry_times[file_id]
            self.staged_urls[file_id] = response
            self.message_display.display(f"File {file_id} is ready for download.")
        elif isinstance(response, RetryResponse):
            self.unstaged_retry_times[file_id] = perf_counter() + response.retry_after
            self.message_display.display(f"File {file_id} is (still) being staged.")
        else:
            self.missing_files.append(file_id)

    def _check_timeout(self):
        """Check whether we have waited too long for the files to be staged.

        In that cases, a MaxWaitTimeExceededError is raised.
        """
        if perf_counter() - self.started_waiting >= self.max_wait_time:
            raise exceptions.MaxWaitTimeExceededError(max_wait_time=self.max_wait_time)

    def _handle_failures(self) -> bool:
        """Handle failed downloads and either abort or proceed based on user input.

        Returns whether there was user interaction.
        Raises an error if the user chose to abort the download.
        """
        if not self.missing_files or self.ignore_failed:
            return False
        missing = ", ".join(self.missing_files)
        message = f"No download exists for the following file IDs: {missing}"
        self.message_display.failure(message)
        if self.finished:
            return False
        unknown_ids_present = (
            "Some of the provided file IDs cannot be downloaded."
            + "\nDo you want to proceed ?\n[Yes][No]\n"
        )
        response = self.io_handler.get_input(message=unknown_ids_present)
        self.io_handler.handle_response(response=response)
        self.message_display.display("Downloading remaining files")
        self.started_waiting = perf_counter()  # reset the timer
        self.missing_files = []  # reset list of missing files
        return True
