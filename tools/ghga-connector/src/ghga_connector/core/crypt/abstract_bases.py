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

"""Base classes for encryption/decryption functionality"""

from abc import ABC, abstractmethod
from collections.abc import Generator
from io import BufferedReader
from pathlib import Path


class Decryptor(ABC):
    """Convenience class to deal with file decryption"""

    @abstractmethod
    def decrypt_file(self, *, input_path: Path, output_path: Path):
        """Decrypt provided file"""


class Encryptor(ABC):
    """Handles on the fly encryption and checksum calculation"""

    @abstractmethod
    def get_encrypted_size(self) -> int:
        """Get file size after encryption, excluding envelope"""

    @abstractmethod
    def process_file(self, file: BufferedReader) -> Generator[bytes, None, None]:
        """Encrypt file parts and prepare for upload."""
