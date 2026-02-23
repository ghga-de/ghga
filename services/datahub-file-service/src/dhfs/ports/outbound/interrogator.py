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

"""Contains a port definition for file interrogation class"""

from abc import ABC, abstractmethod

from pydantic import UUID4, SecretBytes

from dhfs.models import FileUpload


class InterrogatorPort(ABC):
    """A class that inspects and re-encrypts files and places them in the interrogation bucket."""

    class CantCompleteError(RuntimeError):
        """Base error class for errors that prevent the interrogation process from
        completing before a conclusion can be reached about the outcome.
        """

    class FileNotFoundError(CantCompleteError):
        """Raised when a file isn't found in the inbox"""

        def __init__(self, *, file_id: UUID4, object_id: UUID4):
            msg = f"The file {file_id}, under object ID {object_id} was not found in the inbox"
            super().__init__(msg)

    class ReencryptionError(CantCompleteError):
        """Raised when there's a problem during re-encryption. This is more likely
        caused by a code flaw than a problem with the file itself.
        """

    class InterrogationError(RuntimeError):
        """Base error class for errors that ultimately signal interrogation failure"""

    class FileEnvelopeDecryptionError(InterrogationError):
        """Raised when the file envelope can't be decrypted"""

        def __init__(self, *, file_id: UUID4):
            msg = f"Failed to decrypt the Crypt4GH envelope for file {file_id}"
            super().__init__(msg)

    class DecryptionError(InterrogationError):
        """Raised when a file part can't be decrypted"""

    class DecryptedChecksumMismatchError(InterrogationError):
        """Raised when the SHA256 checksums over the unencrypted content don't match."""

        def __init__(self, *, file_id: UUID4):
            msg = (
                f"The SHA-256 checksum over unencrypted content for file {file_id}"
                + " doesn't match the value submitted with the file"
            )
            super().__init__(msg)

    class EncryptedChecksumMismatchError(InterrogationError):
        """Raised when the MD5 checksums over the encrypted content don't match"""

        def __init__(self, *, file_id: UUID4):
            msg = (
                f"The S3 ETag (MD5 checksum) for file {file_id} doesn't match the"
                + " locally calculated value."
            )
            super().__init__(msg)

    @abstractmethod
    async def interrogate_new_files(self) -> None:
        """Query the GHGA Central API for new files that need to be re-encrypted.

        This method handles InterrogationError exceptions by reporting failures to the
        Central API. CantCompleteError exceptions propagate up to the caller.

        Raises:
        - CantCompleteError if an error prevents interrogation from completing (e.g., network issues, S3 unavailable).
        """
        ...

    @abstractmethod
    async def interrogate_file(self, file_upload: FileUpload) -> None:
        """Inspect and re-encrypt a newly uploaded file.

        Raises:
        - FileEnvelopeDecryptionError if the Crypt4GH envelope cannot be decrypted.
        - DecryptionError if a file part cannot be decrypted.
        - ReencryptionError if re-encryption fails.
        - ChecksumMismatchError if checksums don't match expected values.
        - CantCompleteError if an error prevents interrogation from completing.
        - InterrogationError for other errors that signal interrogation failure.
        """
        ...

    @abstractmethod
    async def report_success(  # noqa: PLR0913
        self,
        *,
        file_id: UUID4,
        bucket_id: str,
        object_id: UUID4,
        secret: SecretBytes,
        encrypted_parts_md5: list[bytes],
        encrypted_parts_sha256: list[bytes],
    ) -> None:
        """Submit an InterrogationReport for a successful interrogation.

        Raises:
        - May raise errors from the Central API client if report submission fails.
        """
        ...

    @abstractmethod
    async def report_failure(self, *, file_id: UUID4, reason: str) -> None:
        """Submit an InterrogationReport for an unsuccessful interrogation.

        Raises:
        - May raise errors from the Central API client if report submission fails.
        """
        ...
