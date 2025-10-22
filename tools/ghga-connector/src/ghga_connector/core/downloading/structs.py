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
#
"""Contains additional data structures needed by the download code"""

from dataclasses import dataclass
from pathlib import Path

from ghga_connector.constants import C4GH


@dataclass
class RetryResponse:
    """Response to download request if file is not yet staged"""

    retry_after: int


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
