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

"""Core logic for file re-encryption and interrogation"""

import io
import logging
import os
from uuid import UUID, uuid4

import crypt4gh.header
import crypt4gh.lib
from crypt4gh.keys import get_private_key
from hexkit.utils import now_utc_ms_prec
from nacl.bindings import (
    crypto_aead_chacha20poly1305_ietf_decrypt as decrypt_algo,
)
from nacl.bindings import (
    crypto_aead_chacha20poly1305_ietf_encrypt as encrypt_algo,
)
from pydantic import UUID4, SecretBytes

from dhfs.config import Config
from dhfs.constants import ENCRYPTION_SECRET_LENGTH, NONCE_LENGTH
from dhfs.core.checksums import Checksums
from dhfs.core.models import FileUpload, InterrogationReport, PartRange
from dhfs.ports.outbound.central import CentralClientPort
from dhfs.ports.outbound.interrogator import InterrogatorPort
from dhfs.ports.outbound.s3 import S3ClientPort

log = logging.getLogger(__name__)


class Interrogator(InterrogatorPort):
    """Inspects and re-encrypts newly uploaded files"""

    def __init__(
        self,
        *,
        config: Config,
        central_client: CentralClientPort,
        s3_client: S3ClientPort,
    ):
        """Initialize the Interrogator"""
        self._storage_alias = config.storage_alias
        self._interrogation_bucket_id = config.interrogation_bucket_id
        self._central_client = central_client
        self._data_hub_private_key = SecretBytes(
            get_private_key(
                config.data_hub_crypt4gh_private_key_path,
                lambda: config.crypt4gh_private_key_passphrase,
            )
        )
        self._s3_client = s3_client

    async def interrogate_new_files(self) -> None:
        """Query the GHGA Central API for new files that need to be re-encrypted.

        This method handles InterrogationError exceptions by reporting failures to the
        Central API. CantCompleteError exceptions propagate up to the caller.

        Raises:
        - CantCompleteError if an error prevents interrogation from completing (e.g., network issues, S3 unavailable).
        """
        new_files = await self._central_client.fetch_new_uploads()
        for file in new_files:
            try:
                # Verify that the file exists in the inbox before proceeding
                if not await self._s3_client.get_is_file_in_inbox(file=file):
                    raise self.FileNotFoundError(
                        file_id=file.id, object_id=file.object_id
                    )
                await self.interrogate_file(file)
            except self.InterrogationError as err:
                reason = getattr(err, "reason", None) or "Unexpected error"
                await self.report_failure(file_id=file.id, reason=reason)

    async def _fetch_original_secret(self, *, file_upload: FileUpload) -> SecretBytes:
        """Fetch the original file encryption secret.

        Raises:
        - BucketNotFoundError if the inbox bucket doesn't exist.
        - ObjectNotFoundError if the file doesn't exist in the inbox.
        - DownloadError if the download request fails.
        - CryptoError if the Crypt4GH envelope cannot be decrypted.
        - ValueError if the secrets list returned by Crypt4GH is not 1 element long.
        """
        envelope = await self._s3_client.fetch_file_content_range(
            bucket_id=file_upload.bucket_id,
            object_id=str(file_upload.object_id),
            start=0,
            stop=file_upload.offset,
        )
        return self._extract_secret(envelope=envelope)

    def _extract_secret(self, *, envelope: bytes) -> SecretBytes:
        """Extract file encryption/decryption secret from envelope.

        Raises:
        - CryptoError if the envelope cannot be decrypted with the data hub's private key.
        - ValueError if the secrets list returned by Crypt4GH is not 1 element long.
        """
        envelope_stream = io.BytesIO(envelope)
        keys = [(0, self._data_hub_private_key.get_secret_value(), None)]
        session_keys, _ = crypt4gh.header.deconstruct(
            infile=envelope_stream, keys=keys, sender_pubkey=None
        )
        if (count := len(session_keys)) != 1:
            raise ValueError(f"Expected session key count to be 1, not {count}")
        return SecretBytes(session_keys[0])

    async def _fetch_and_decrypt_part(
        self,
        *,
        bucket_id: str,
        object_id: str,
        part_range: PartRange,
        secret: SecretBytes,
    ) -> bytes:
        """Download and decrypt a single file part.

        Raises:
        - BucketNotFoundError if the inbox bucket doesn't exist.
        - ObjectNotFoundError if the file doesn't exist in the inbox.
        - DownloadError if the download request fails.
        - DecryptionError if the part cannot be decrypted (wrapped from underlying exceptions).
        """
        part = await self._s3_client.fetch_file_content_range(
            bucket_id=bucket_id,
            object_id=object_id,
            start=part_range.start,
            stop=part_range.stop,
        )
        return self._decrypt_part(encrypted_part=part, secret=secret)

    def _decrypt_part(self, *, encrypted_part: bytes, secret: SecretBytes) -> bytes:
        """Decrypt an encrypted file part with the given key.

        May raise exceptions from the underlying decrypt_algo if decryption fails.
        """
        buffer = bytearray()
        part_size = len(encrypted_part)
        position = 0

        while position < part_size:
            chunk = encrypted_part[
                position : position + crypt4gh.lib.CIPHER_SEGMENT_SIZE
            ]
            buffer += decrypt_algo(
                chunk[NONCE_LENGTH:],  # data to decrypt (after nonce)
                None,
                chunk[:NONCE_LENGTH],  # nonce (first 12 bytes)
                secret.get_secret_value(),
            )
            position += crypt4gh.lib.CIPHER_SEGMENT_SIZE
        return bytes(buffer)

    def _reencrypt_part(
        self, *, decrypted_part: bytes, new_secret: SecretBytes
    ) -> bytes:
        """Re-encrypt a decrypted file part using a new secret.

        May raise exceptions from the underlying encrypt_algo if re-encryption fails.
        """
        buffer = bytearray()
        part_size = len(decrypted_part)
        position = 0

        while position < part_size:
            # Extract plaintext chunk (up to SEGMENT_SIZE bytes of decrypted data)
            chunk = decrypted_part[position : position + crypt4gh.lib.SEGMENT_SIZE]
            nonce = os.urandom(NONCE_LENGTH)
            encrypted = encrypt_algo(chunk, None, nonce, new_secret.get_secret_value())
            buffer += nonce + encrypted
            position += crypt4gh.lib.SEGMENT_SIZE

        return bytes(buffer)

    async def _process_file_parts(  # noqa: C901
        self,
        *,
        file_upload: FileUpload,
        new_object_id: str,
        upload_id: str,
        old_secret: SecretBytes,
        new_secret: SecretBytes,
    ) -> Checksums:
        """Perform the decrypt/re-encrypt/decrypt/upload cycle on each file part.

        Returns the `Checksums` object containing the checksums calculated during
        the file processing. All error translation is done here, but all S3 cleanup is
        handled from the calling function, `interrogate_file()`.

        Raises:
        - DecryptionError if a file part cannot be decrypted.
        - ReencryptionError if re-encryption fails.
        - CantCompleteError if an S3 InconclusiveError occurs during upload.
        - InterrogationError if an S3 ConclusiveError occurs during upload.
        - BucketNotFoundError if the inbox bucket doesn't exist.
        - ObjectNotFoundError if the file doesn't exist in the inbox.
        - DownloadError if download requests fail.
        """
        # Establish Checksums object to track decrypted and encrypted content checksums
        checksums = Checksums()
        file_id = file_upload.id
        inbox_object_id = str(file_upload.object_id)
        upload_buffer = bytearray()
        uploaded_part_number = 1

        log_extra = {  # only for logging purposes
            "file_id": file_id,
            "inbox_object_id": inbox_object_id,
            "interrogation_object_id": new_object_id,
        }

        # Download, re-encrypt, and upload object part-by-part
        for part_no, part_range in enumerate(file_upload.calc_encrypted_part_ranges()):
            log.debug("Processing part %s for file %s", part_no, file_id)

            # Initial decryption
            try:
                decrypted_part = await self._fetch_and_decrypt_part(
                    bucket_id=file_upload.bucket_id,
                    object_id=inbox_object_id,
                    part_range=part_range,
                    secret=old_secret,
                )
            except Exception as err:
                log.error(
                    "Failed initial decryption of chunk number %i of file %s",
                    part_no,
                    file_id,
                    exc_info=True,
                    extra=log_extra,
                )
                raise self.DecryptionError() from err

            # Re-encrypt
            try:
                reencrypted_part = self._reencrypt_part(
                    decrypted_part=decrypted_part, new_secret=new_secret
                )
            except Exception as err:
                log.error(
                    "Failed to re-encrypt part number %i for file %s.",
                    part_no,
                    file_id,
                    exc_info=True,
                    extra=log_extra,
                )
                raise self.ReencryptionError() from err

            # Decrypt again to verify encryption process was correct
            try:
                decrypted_part = self._decrypt_part(
                    encrypted_part=reencrypted_part, secret=new_secret
                )
            except Exception as err:
                log.error(
                    "Failed confirmatory decryption of chunk number %i of file %s",
                    part_no,
                    file_id,
                    exc_info=True,
                    extra=log_extra,
                )
                raise self.DecryptionError() from err

            # Update whole-decrypted-file sha256
            checksums.update_unencrypted(decrypted_part)

            upload_buffer += reencrypted_part
            if len(upload_buffer) >= file_upload.adjusted_part_size:
                # Calculate part's encrypted md5 and sha256
                part_to_upload = bytes(upload_buffer[: file_upload.adjusted_part_size])
                checksums.update_encrypted(part_to_upload)

                # Upload the re-encrypted part
                try:
                    await self._s3_client.upload_file_part(
                        upload_id=upload_id,
                        object_id=new_object_id,
                        part_no=uploaded_part_number,
                        part_md5=checksums.encrypted_md5[-1],
                        part=part_to_upload,
                    )
                    uploaded_part_number += 1
                except S3ClientPort.InconclusiveError as err:
                    raise self.CantCompleteError() from err
                except S3ClientPort.ConclusiveError as err:
                    raise self.InterrogationError() from err

                # Set buffer to whatever the remainder was
                upload_buffer = upload_buffer[file_upload.adjusted_part_size :]

        # Upload remaining file content if needed
        if upload_buffer:
            remaining_bytes = bytes(upload_buffer)
            checksums.update_encrypted(remaining_bytes)
            try:
                await self._s3_client.upload_file_part(
                    upload_id=upload_id,
                    object_id=new_object_id,
                    part_no=uploaded_part_number,
                    part_md5=checksums.encrypted_md5[-1],
                    part=remaining_bytes,
                )
            except S3ClientPort.ConclusiveError as error:
                raise self.InterrogationError() from error
            except S3ClientPort.InconclusiveError as error:
                raise self.CantCompleteError() from error

        return checksums

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
        # Extract the file encryption secret and content offset
        try:
            old_secret = await self._fetch_original_secret(file_upload=file_upload)
        except Exception as err:
            # Failed to decrypt envelope - interrogation failed - no cleanup needed
            envelope_error = self.FileEnvelopeDecryptionError(file_id=file_upload.id)
            log.error(envelope_error, exc_info=True)
            raise envelope_error from err

        # Initiate multipart upload
        new_object_id = str(uuid4())
        log.info(
            "Generated %s as the new object ID for file %s.",
            new_object_id,
            file_upload.id,
            extra={
                "file_id": file_upload.id,
                "inbox_object_id": file_upload.object_id,
                "interrogation_object_id": new_object_id,
            },
        )
        try:
            upload_id = await self._s3_client.init_interrogation_bucket_upload(
                object_id=new_object_id
            )
        except S3ClientPort.InconclusiveError as err:
            raise self.CantCompleteError() from err

        # Generate new file encryption secret
        new_secret = SecretBytes(os.urandom(ENCRYPTION_SECRET_LENGTH))

        try:
            # Re-encrypt and upload file parts, obtaining the checksums for the decrypted
            #  and re-encrypted content
            checksums = await self._process_file_parts(
                file_upload=file_upload,
                new_object_id=new_object_id,
                upload_id=upload_id,
                old_secret=old_secret,
                new_secret=new_secret,
            )
        except Exception:  # all exceptions require aborting the upload, just re-raise
            await self._s3_client.abort_upload(
                upload_id=upload_id, object_id=new_object_id
            )
            log.warning("Upload with ID %s was aborted - cleanup complete.", upload_id)
            raise

        # Compare final decrypted content checksum with the user-reported value
        if checksums.unencrypted_sha256.hexdigest() != file_upload.decrypted_sha256:
            await self._s3_client.abort_upload(
                upload_id=upload_id, object_id=new_object_id
            )
            log.warning("Upload with ID %s was aborted - cleanup complete.", upload_id)
            sha256_error = self.DecryptedChecksumMismatchError(file_id=file_upload.id)
            log.error(sha256_error)
            raise sha256_error

        # Complete upload
        try:
            actual_etag = await self._s3_client.complete_upload(
                upload_id=upload_id,
                object_id=new_object_id,
                part_count=len(checksums.encrypted_md5),
            )
        except S3ClientPort.InconclusiveError as err:
            await self._s3_client.abort_upload(
                upload_id=upload_id, object_id=new_object_id
            )
            log.warning("Upload with ID %s was aborted - cleanup complete.", upload_id)
            raise self.CantCompleteError() from err
        except S3ClientPort.ConclusiveError as err:
            await self._s3_client.abort_upload(
                upload_id=upload_id, object_id=new_object_id
            )
            log.warning("Upload with ID %s was aborted - cleanup complete.", upload_id)
            raise self.InterrogationError() from err

        # Check integrity of final object in S3
        expected_etag = checksums.encrypted_checksum_for_s3()
        if expected_etag != actual_etag:
            md5_error = self.EncryptedChecksumMismatchError(file_id=file_upload.id)
            log.error(
                md5_error,
                extra={
                    "file_id": file_upload.id,
                    "inbox_object_id": file_upload.object_id,
                    "interrogation_object_id": new_object_id,
                },
            )
            await self._s3_client.remove_file(object_id=new_object_id)
            log.warning(
                "File %s removed from interrogation bucket - cleanup complete.",
                new_object_id,
            )
            raise md5_error

        # Issue report to Central API containing new encryption secret and checksums
        await self.report_success(
            file_id=file_upload.id,
            bucket_id=self._interrogation_bucket_id,
            object_id=UUID(new_object_id),
            secret=new_secret,
            encrypted_parts_md5=checksums.encrypted_md5,
            encrypted_parts_sha256=checksums.encrypted_sha256,
            encrypted_size=file_upload.encrypted_size - file_upload.offset,
        )

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

        Raises:
        - May raise errors from the Central API client if report submission fails.
        """
        report = InterrogationReport(
            file_id=file_id,
            storage_alias=self._storage_alias,
            bucket_id=bucket_id,
            object_id=object_id,
            interrogated_at=now_utc_ms_prec(),
            passed=True,
            secret=secret,
            encrypted_parts_md5=[h.hex() for h in encrypted_parts_md5],
            encrypted_parts_sha256=[h.hex() for h in encrypted_parts_sha256],
            encrypted_size=encrypted_size,
        )
        try:
            await self._central_client.submit_interrogation_report(report=report)
        except CentralClientPort.CentralAPIError:
            await self._s3_client.remove_file(object_id=str(object_id))
            log.warning(
                "Interrogation report submission failed for file %s, so the file"
                + " was removed from the interrogation bucket. Interrogation will have"
                + " to be repeated.",
                file_id,
            )
            raise

    async def report_failure(self, *, file_id: UUID4, reason: str) -> None:
        """Submit an InterrogationReport for an unsuccessful interrogation.

        Raises:
        - May raise errors from the Central API client if report submission fails.
        """
        report = InterrogationReport(
            file_id=file_id,
            storage_alias=self._storage_alias,
            interrogated_at=now_utc_ms_prec(),
            passed=False,
            reason=reason,
        )
        await self._central_client.submit_interrogation_report(report=report)
