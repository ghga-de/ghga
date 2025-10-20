# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter, sleep

from ghga_connector import exceptions
from ghga_connector.config import Config, get_download_api_url
from ghga_connector.constants import C4GH
from ghga_connector.core import CLIMessageDisplay, WorkPackageClient
from ghga_connector.core.api_calls import is_service_healthy

from .api_calls import DownloadClient
from .structs import RetryResponse


@dataclass
class CliIoHandler:
    """Convenience class to hold both input and output handlers"""

    file_ids_with_extension: dict[str, str] = field(default_factory=dict, init=False)

    def check_output(self, *, location: Path) -> list[str]:
        """Check for and return existing files in output directory."""
        existing_files = []

        # check local files with and without extension
        for file_id, file_extension in self.file_ids_with_extension.items():
            if file_extension:
                file = location / f"{file_id}{file_extension}{C4GH}"
            else:
                file = location / f"{file_id}{C4GH}"

            if file.exists():
                existing_files.append(file_id)

        return existing_files

    def get_input(self, *, message: str) -> str:
        """Simple user input handling."""
        return input(message)

    def handle_response(self, *, response: str):
        """Handle response from get_input."""
        if not (response.lower() == "yes" or response.lower() == "y"):
            raise exceptions.AbortBatchProcessError()


@dataclass
class FileInfo:
    """Information about a file to be downloaded"""

    file_id: str
    file_extension: str
    file_size: int
    output_dir: Path

    @property
    def file_name(self) -> str:
        """Construct file name with suffix, if given"""
        file_name = f"{self.file_id}"
        if self.file_extension:
            file_name = f"{self.file_id}{self.file_extension}"
        return file_name

    @property
    def path_during_download(self) -> Path:
        """The file path while the file download is still in progress"""
        # with_suffix() might overwrite existing suffixes, do this instead:
        output_file = self.path_once_complete
        return output_file.parent / (output_file.name + ".part")

    @property
    def path_once_complete(self) -> Path:
        """The file path once the download is complete"""
        return self.output_dir / f"{self.file_name}{C4GH}"


class FileStager:
    """Utility class to deal with file staging in batch processing."""

    def __init__(
        self,
        *,
        wanted_files: dict[str, str],
        output_dir: Path,
        work_package_client: WorkPackageClient,
        download_client: DownloadClient,
        config: Config,
    ):
        """Initialize the FileStager."""
        self._io_handler = CliIoHandler()
        existing_file_ids = set(self._io_handler.check_output(location=output_dir))
        self._file_ids_with_extensions = wanted_files
        self._output_dir = output_dir
        self._download_api_url = get_download_api_url()
        if not is_service_healthy(self._download_api_url):
            raise exceptions.ApiNotReachableError(api_url=self._download_api_url)
        self._work_package_client = work_package_client
        self._download_client = download_client
        self._max_wait_time = config.max_wait_time
        self._started_waiting = now = perf_counter()

        # Successfully staged files info -- in the beginning, consider all file as
        #  staged with a retry time of 0
        self._staged_files: list[FileInfo] = []

        # Files that are currently being staged with retry times:
        self._unstaged_retry_times = {
            file_id: now for file_id in wanted_files if file_id not in existing_file_ids
        }
        # Files that could not be staged because they cannot be found:
        self._missing_files: list[str] = []
        self._ignore_failed = False

    async def get_staged_files(self) -> list[FileInfo]:
        """Get files that are already staged.

        Returns a dict with file IDs as keys and FileInfo as values.
        These values contain the download URLs and file sizes.
        The dict should be cleared after these files have been downloaded.
        """
        CLIMessageDisplay.display("Updating list of staged files...")
        staging_items = list(self._unstaged_retry_times.items())
        for file_id, retry_time in staging_items:
            if perf_counter() >= retry_time:
                await self._check_file_is_in_download_bucket(file_id=file_id)
            if len(self._staged_files) > 0:
                self._started_waiting = perf_counter()  # reset wait timer
                break
        if not self._staged_files and not self._handle_failures():
            sleep(1)
        self._check_timeout()
        return self._staged_files

    @property
    def finished(self) -> bool:
        """Check whether work is finished, i.e. no staged or unstaged files remain."""
        return not (self._staged_files or self._unstaged_retry_times)

    async def _check_file_is_in_download_bucket(self, file_id: str) -> None:
        """Check whether a file with the given file_id is staged to the Download bucket
        in object storage.

        The method returns nothing, but adapts the internal state accordingly.
        Particularly, files that cannot be found are added to missing_files.

        Raises:
            BadResponseCodeError: If files cannot be staged for reasons other than above.
            NoS3AccessMethodError: If the DRS object for the file doesn't have an S3 access method.
        """
        try:
            response = await self._download_client.get_drs_object(file_id)
        except exceptions.FileNotRegisteredError:
            # The Download API returned a 404, meaning it doesn't recognize the file id
            self._missing_files.append(file_id)
            return

        if isinstance(response, RetryResponse):
            # The file is not staged to the download bucket yet
            self._unstaged_retry_times[file_id] = perf_counter() + response.retry_after
            CLIMessageDisplay.display(f"File {file_id} is (still) being staged.")
            return

        # File is staged and ready for download - add FileInfo instance to dict.
        #  Also, response is a DRS object -- get file size from it
        file_size = response["size"]
        del self._unstaged_retry_times[file_id]
        self._staged_files.append(
            FileInfo(
                file_id=file_id,
                file_extension=self._file_ids_with_extensions[file_id],
                file_size=file_size,
                output_dir=self._output_dir,
            )
        )
        CLIMessageDisplay.display(f"File {file_id} is ready for download.")

    def _check_timeout(self):
        """Check whether we have waited too long for the files to be staged.

        In that cases, a MaxWaitTimeExceededError is raised.
        """
        if perf_counter() - self._started_waiting >= self._max_wait_time:
            raise exceptions.MaxWaitTimeExceededError(max_wait_time=self._max_wait_time)

    def _handle_failures(self) -> bool:
        """Handle failed downloads and either abort or proceed based on user input.

        Returns whether there was user interaction.
        Raises an error if the user chose to abort the download.
        """
        if not self._missing_files or self._ignore_failed:
            return False
        missing = ", ".join(self._missing_files)
        message = f"No download exists for the following file IDs: {missing}"
        CLIMessageDisplay.failure(message)
        if self.finished:
            return False
        unknown_ids_present = (
            "Some of the provided file IDs cannot be downloaded."
            + "\nDo you want to proceed ?\n[Yes][No]\n"
        )
        response = self._io_handler.get_input(message=unknown_ids_present)
        self._io_handler.handle_response(response=response)
        CLIMessageDisplay.display("Downloading remaining files")
        self._started_waiting = perf_counter()  # reset the timer
        self._missing_files = []  # reset list of missing files
        return True
