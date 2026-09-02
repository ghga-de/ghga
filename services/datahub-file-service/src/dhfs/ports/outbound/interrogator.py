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

from dhfs.core.models import FileUpload


class InterrogatorPort(ABC):
    """A class that inspects and re-encrypts files and places them in the interrogation bucket."""

    class InconclusiveError(RuntimeError):
        """Base error class for errors that prevent the interrogation process from
        completing before a conclusion can be reached about the outcome.
        """

    class CriticalError(RuntimeError):
        """A version of CantCompleteError that indicates DHFS should not start a new
        file processing batch.
        """

    class ConclusiveError(RuntimeError):
        """Base error class for errors that ultimately signal interrogation failure"""

        def __init__(self, reason: str | None):
            self.reason = (
                reason or "There was a problem uploading the re-encrypted file."
            )
            super().__init__(self.reason)

    class FileEnvelopeDecryptionError(ConclusiveError):
        """Raised when the file envelope can't be decrypted"""

        def __init__(self):
            msg = "Could not decrypt the file envelope."
            super().__init__(msg)

    class DecryptionError(ConclusiveError):
        """Raised when a file part can't be decrypted"""

        def __init__(self):
            msg = "Failed to decrypt the file content."
            super().__init__(msg)

    class DecryptedChecksumMismatchError(ConclusiveError):
        """Raised when the SHA256 checksums over the unencrypted content don't match."""

        def __init__(self):
            msg = (
                "The SHA-256 checksum over unencrypted content does not match"
                + " the value submitted with the file."
            )
            super().__init__(msg)

    @abstractmethod
    def close(self) -> None:
        """Release any resources the interrogator holds. Safe to call more than once.

        Declared on the port so callers holding only it see the teardown obligation.
        """
        ...

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
        encrypted_size: int,
    ) -> None:
        """Submit an InterrogationReport for a successful interrogation.

        Submission errors are logged but not raised; the re-encrypted file is
        left in the interrogation bucket regardless of outcome so that it is not
        re-processed with a different secret on the next invocation.
        """
        ...

    @abstractmethod
    async def report_failure(self, *, file_id: UUID4, reason: str) -> None:
        """Submit an InterrogationReport for an unsuccessful interrogation.

        Submission errors are logged but not raised so that processing of
        remaining files in the batch is not interrupted.
        """
        ...
