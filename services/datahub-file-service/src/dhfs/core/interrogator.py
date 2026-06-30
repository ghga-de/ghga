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

from dhfs.adapters.outbound.http import ConnectionFailedError
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
                lambda: config.data_hub_crypt4gh_private_key_passphrase,
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
        try:
            new_files = await self._central_client.fetch_new_uploads()
        except CentralClientPort.UpgradeRequiredError as err:
            raise self.CriticalError(err) from err
        except ConnectionFailedError as err:
            log.error("Unable to reach the GHGA Central API (%s).", str(err))
            return
        except CentralClientPort.CentralAPIError as err:
            log.error("The GHGA Central API returned an error response: %s", err)
            return
        except CentralClientPort.ResponseFormatError as err:
            log.error(
                "The GHGA Central API returned an unrecognized response format: %s", err
            )
            return

        log.info("Received a batch of %i file(s) to process.", len(new_files))
        for file in new_files:
            try:
                # Verify that the file exists in the inbox before proceeding
                if not await self._s3_client.get_is_file_in_inbox(file=file):
                    raise self.InconclusiveError(
                        f"The file {file.id}, under object ID {file.object_id} was not"
                        + " found in the inbox"
                    )
                await self.interrogate_file(file)
            except self.ConclusiveError as err:
                reason = getattr(err, "reason", None) or "Unexpected error"
                # Errors in .report_failure() are logged without re-raising, because
                #  the solution to the error is simply to move on to the next file
                await self.report_failure(file_id=file.id, reason=reason)
            except self.InconclusiveError as err:
                log.warning(
                    "File %s: Unable to conclusively process file - will retry later. Reason: %s",
                    file.id,
                    err,
                )
        log.info("Finished processing current file batch.")

    async def _fetch_original_secret(self, *, file_upload: FileUpload) -> SecretBytes:
        """Fetch the original file encryption secret.

        Raises:
        - InconclusiveError if the file doesn't exist in the inbox or if the download
            request fails.
        - FileEnvelopeDecryptionError if the Crypt4GH envelope cannot be decrypted or
            if the secrets list returned by Crypt4GH is not 1 element long.
        """
        try:
            envelope = await self._s3_client.fetch_file_content_range(
                bucket_id=file_upload.bucket_id,
                object_id=str(file_upload.object_id),
                start=0,
                stop=file_upload.offset,
            )
        except S3ClientPort.S3OperationError as err:
            raise self.InconclusiveError(err) from err
        except S3ClientPort.CriticalS3Error as err:
            raise self.CriticalError(err) from err

        try:
            return self._extract_secret(envelope=envelope)
        except ValueError as err:
            # Failed to decrypt envelope - interrogation failed - no cleanup needed
            raise self.FileEnvelopeDecryptionError() from err

    def _extract_secret(self, *, envelope: bytes) -> SecretBytes:
        """Extract file encryption/decryption secret from envelope.

        Raises:
        - ValueError if the envelope cannot be decrypted with the data hub's private
            key or if the secrets list returned by Crypt4GH is not 1 element long.
        """
        envelope_stream = io.BytesIO(envelope)
        keys = [(0, self._data_hub_private_key.get_secret_value(), None)]
        session_keys, _ = crypt4gh.header.deconstruct(
            infile=envelope_stream, keys=keys, sender_pubkey=None
        )
        if (count := len(session_keys)) != 1:
            raise ValueError(f"Expected session key count to be 1, not {count}")

        # crypt4gh v1.8.6 returns session key as bytearray instead of bytes
        return SecretBytes(bytes(session_keys[0]))

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
        - DecryptionError if the part cannot be decrypted.
        """
        try:
            part = await self._s3_client.fetch_file_content_range(
                bucket_id=bucket_id,
                object_id=object_id,
                start=part_range.start,
                stop=part_range.stop,
            )
        except S3ClientPort.S3OperationError as err:
            raise self.InconclusiveError(err) from err
        except S3ClientPort.CriticalS3Error as err:
            raise self.CriticalError(err) from err
        return self._decrypt_part(encrypted_part=part, secret=secret)

    def _decrypt_part(self, *, encrypted_part: bytes, secret: SecretBytes) -> bytes:
        """Decrypt an encrypted file part with the given key.

        Raises DecryptionError if decryption fails.
        """
        buffer = bytearray()
        part_size = len(encrypted_part)
        position = 0

        try:
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
        except Exception as err:
            # We do a catch-all here on purpose - decrypt_algo can raise several error types
            raise self.DecryptionError() from err

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

    async def _process_file_parts(  # noqa: C901, PLR0915
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
            "reencrypted_object_id": new_object_id,
        }

        # Download, re-encrypt, and upload object part-by-part
        for part_no, part_range in enumerate(
            file_upload.calc_encrypted_part_ranges(), start=1
        ):
            log.debug("File %s: Processing part %s.", file_id, part_no)
            log_extra["file_part_number"] = part_no
            log_extra["content_range"] = f"{part_range.start}-{part_range.stop}"

            # Initial decryption
            try:
                decrypted_part = await self._fetch_and_decrypt_part(
                    bucket_id=file_upload.bucket_id,
                    object_id=inbox_object_id,
                    part_range=part_range,
                    secret=old_secret,
                )
            except Exception as err:
                # Catch-all is intentional, see comments below
                log.warning(
                    "File %s: Failed to get and decrypt part number %i.",
                    file_id,
                    part_no,
                    extra=log_extra,
                )
                # If we've already translate the underlying error, just re-raise as is
                if isinstance(err, (self.InconclusiveError, self.ConclusiveError)):
                    raise
                if isinstance(err, S3ClientPort.CriticalS3Error):
                    raise self.CriticalError(err) from err
                # Otherwise, translate to inconclusive error - we don't know what went
                #  wrong and didn't expect it, so we can't conclude that the file is bad
                raise self.InconclusiveError(err) from err

            # Re-encrypt
            try:
                reencrypted_part = self._reencrypt_part(
                    decrypted_part=decrypted_part, new_secret=new_secret
                )
            except Exception as err:
                log.warning(
                    "File %s: Failed to re-encrypt a file part.",
                    file_id,
                    extra=log_extra,
                )
                raise self.InconclusiveError(err) from err

            # Decrypt again to verify encryption process was correct
            try:
                decrypted_part = self._decrypt_part(
                    encrypted_part=reencrypted_part, secret=new_secret
                )
            except Exception as err:
                log.warning(
                    "File %s: A file part seems incorrectly re-encrypted.",
                    file_id,
                    extra=log_extra,
                )
                raise self.InconclusiveError(err) from err

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
                    log.debug(
                        "File %s: Uploaded S3 part %i.",
                        file_id,
                        uploaded_part_number,
                        extra=log_extra,
                    )
                    uploaded_part_number += 1
                except S3ClientPort.S3OperationError as err:
                    raise self.InconclusiveError(err) from err
                except S3ClientPort.CriticalS3Error as err:
                    raise self.CriticalError(err) from err

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
                log.debug(
                    "File %s: Uploaded S3 part %i.",
                    file_id,
                    uploaded_part_number,
                    extra=log_extra,
                )
            except S3ClientPort.S3OperationError as err:
                raise self.InconclusiveError(err) from err
            except S3ClientPort.CriticalS3Error as err:
                raise self.CriticalError(err) from err

        log.debug(
            "File %s: All %i file part(s) uploaded to S3.",
            file_id,
            len(checksums.encrypted_md5),
            extra=log_extra,
        )
        return checksums

    async def interrogate_file(self, file_upload: FileUpload) -> None:
        """Inspect and re-encrypt a newly uploaded file.

        Raises:
        - FileEnvelopeDecryptionError if the Crypt4GH envelope cannot be decrypted.
        - DecryptionError if a file part cannot be decrypted.
        - ChecksumMismatchError if checksums don't match expected values.
        - CantCompleteError if an error prevents interrogation from completing.
        - UploadCompletionError if there's an error while trying to conclude the upload.
        """
        # Extract the file encryption secret and content offset
        log.debug(
            "File %s: Fetching original symmetric encryption secret from file envelope.",
            file_upload.id,
        )
        # Error handling performed inside ._fetch_original_secret()
        old_secret = await self._fetch_original_secret(file_upload=file_upload)

        # Initiate multipart upload
        new_object_id = str(uuid4())
        log.debug(
            "File %s: Generated %s as the new object ID.",
            file_upload.id,
            new_object_id,
            extra={
                "file_id": file_upload.id,
                "inbox_object_id": file_upload.object_id,
                "reencrypted_object_id": new_object_id,
            },
        )
        try:
            upload_id = await self._s3_client.init_interrogation_bucket_upload(
                object_id=new_object_id
            )
            log.info(
                "File %s: Created multipart upload.",
                file_upload.id,
                extra={"reencrypted_object_id": new_object_id, "upload_id": upload_id},
            )
        except S3ClientPort.S3OperationError as err:
            raise self.InconclusiveError(err) from err
        except S3ClientPort.CriticalS3Error as err:
            raise self.CriticalError(err) from err

        # Generate new file encryption secret
        new_secret = SecretBytes(os.urandom(ENCRYPTION_SECRET_LENGTH))
        log.debug("File %s: Generated new encryption secret.", file_upload.id)

        try:
            # Re-encrypt and upload file parts, obtaining the checksums for the decrypted
            #  and re-encrypted content
            log.info(
                "File %s: Starting decryption/re-encryption process.",
                file_upload.id,
            )
            # Error translation handled inside ._process_file_parts()
            checksums = await self._process_file_parts(
                file_upload=file_upload,
                new_object_id=new_object_id,
                upload_id=upload_id,
                old_secret=old_secret,
                new_secret=new_secret,
            )
        except Exception:  # all exceptions require aborting the upload, just re-raise
            await self._clean_up_upload(
                upload_id=upload_id, object_id=new_object_id, file_id=file_upload.id
            )
            raise

        # Compare final decrypted content checksum with the user-reported value
        if checksums.unencrypted_sha256.hexdigest() != file_upload.decrypted_sha256:
            log.warning(
                "File %s: Unable to re-encrypt: sha256 checksum of decrypted content"
                + " doesn't match user-reported value.",
                file_upload.id,
            )
            await self._clean_up_upload(
                upload_id=upload_id, object_id=new_object_id, file_id=file_upload.id
            )
            raise self.DecryptedChecksumMismatchError()

        # Complete upload
        log.debug(
            "File %s: Checksums match - completing multipart upload.",
            file_upload.id,
            extra={"file_id": file_upload.id, "upload_id": upload_id},
        )
        try:
            etag_of_reencrypted_obj = await self._s3_client.complete_upload(
                upload_id=upload_id,
                object_id=new_object_id,
                part_count=len(checksums.encrypted_md5),
            )
            log.debug(
                "File %s: Multipart upload %s for object ID %s completed.",
                file_upload.id,
                upload_id,
                new_object_id,
            )
        except S3ClientPort.CriticalS3Error as err:
            raise self.CriticalError(err) from err
        except S3ClientPort.S3Error as err:
            await self._clean_up_upload(
                upload_id=upload_id, object_id=new_object_id, file_id=file_upload.id
            )
            raise self.InconclusiveError(err) from err

        # Check integrity of final object in S3
        if checksums.encrypted_checksum_for_s3() != etag_of_reencrypted_obj:
            log.warning(
                "File %s: The S3 ETag (MD5 checksum) doesn't match the locally calculated value.",
                file_upload.id,
                extra={
                    "file_id": file_upload.id,
                    "inbox_object_id": file_upload.object_id,
                    "reencrypted_object_id": new_object_id,
                },
            )
            try:
                await self._s3_client.remove_file(object_id=new_object_id)
            except Exception as exc:
                # Don't re-raise this error because we'll raise a different error below
                log.error(
                    "File %s: Cleanup failed: %s",
                    file_upload.id,
                    exc,
                    extra={
                        "file_id": file_upload.id,
                        "reencrypted_object_id": new_object_id,
                    },
                )
            else:
                log.info(
                    "File %s: Removed object from the '%s' bucket - cleanup complete.",
                    file_upload.id,
                    self._interrogation_bucket_id,
                    extra={
                        "file_id": file_upload.id,
                        "reencrypted_object_id": new_object_id,
                    },
                )

            # This is a problem on our end:
            raise self.InconclusiveError(
                "Encrypted content checksum did not match the expected value. This"
                + " indicates that the data S3 received from DHFS is not what DHFS"
                + " intended to send. This will likely be resolved simply by letting"
                + " DHFS try to process the file again. Nothing else needs to be done."
            )

        # Issue report to Central API containing new encryption secret and checksums
        log.debug(
            "File %s: S3 ETag check passed - submitting success report.",
            file_upload.id,
        )
        await self.report_success(
            file_id=file_upload.id,
            bucket_id=self._interrogation_bucket_id,
            object_id=UUID(new_object_id),
            secret=new_secret,
            encrypted_parts_md5=checksums.encrypted_md5,
            encrypted_parts_sha256=checksums.encrypted_sha256,
            encrypted_size=file_upload.encrypted_size - file_upload.offset,
        )

    async def _clean_up_upload(self, *, upload_id: str, object_id: str, file_id: UUID4):
        """Abort the upload and log but otherwise suppress any errors.

        This method is only called as part of a cleanup process, so there is an
        error already being handled outside of this method. That is why the S3Error
        is only logged.
        """
        try:
            await self._s3_client.abort_upload(upload_id=upload_id, object_id=object_id)
        except S3ClientPort.S3Error as abort_err:
            # Log error but don't raise in order to preserve original error
            log.error(abort_err)
        else:
            log.info(
                "File %s: Aborted upload as part of cleanup (if upload existed).",
                file_id,
                extra={"file_id": file_id, "upload_id": upload_id},
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

        Submission errors are logged but not raised; the re-encrypted file is
        left in the interrogation bucket regardless of outcome so that it is not
        re-processed with a different secret on the next invocation.
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
        except ConnectionFailedError as err:
            raise InterrogatorPort.InconclusiveError(
                "Unable to reach the GHGA Central API.",
            ) from err
        except CentralClientPort.UpgradeRequiredError as err:
            raise InterrogatorPort.CriticalError(err) from err
        # Unlike ConnectionFailedError (report definitely not delivered), these
        # errors require a completed HTTP round-trip, so Central may have processed
        # the report despite returning an error. Raising an InconclusiveError
        # would re-interrogate the file with a different secret (bad), so we log and let
        # the natural retry cycle handle it.
        except CentralClientPort.CentralAPIError as err:
            log.error(
                "File %s: The GHGA Central API returned an error response while"
                + " submitting the file processing report."
                + " DHFS will try re-processing this file later.",
                file_id,
                extra={"err_msg": str(err)},
            )
        except Exception as err:
            # Same reasoning as CentralAPIError above.
            log.error(
                "File %s: Failed to submit file processing report to GHGA Central."
                + " DHFS will try re-processing this file later.",
                file_id,
                extra={"err_msg": str(err)},
            )

    async def report_failure(self, *, file_id: UUID4, reason: str) -> None:
        """Submit an InterrogationReport for an unsuccessful interrogation.

        Submission errors are logged but not raised so that processing of
        remaining files in the batch is not interrupted.
        """
        report = InterrogationReport(
            file_id=file_id,
            storage_alias=self._storage_alias,
            interrogated_at=now_utc_ms_prec(),
            passed=False,
            reason=reason,
        )
        try:
            await self._central_client.submit_interrogation_report(report=report)
        except CentralClientPort.UpgradeRequiredError as err:
            raise InterrogatorPort.CriticalError(err) from err
        except ConnectionFailedError as err:
            log.error(
                "File %s: Unable to reach the GHGA Central API while submitting the"
                + " file processing report. DHFS will try re-processing this file later.",
                file_id,
                extra={"err_msg": str(err)},
            )
        except CentralClientPort.CentralAPIError as err:
            log.error(
                "File %s: The GHGA Central API returned an error response while"
                + " submitting the file processing report."
                + " DHFS will try re-processing this file later.",
                file_id,
                extra={"err_msg": str(err)},
            )
        except Exception as err:
            # This is logged without re-raising, because the solution is simply
            #  to move on to the next file.
            log.error(
                "File %s: Failed to submit file processing report to GHGA Central."
                + " DHFS will try re-processing this file later.",
                file_id,
                extra={"err_msg": str(err)},
            )
