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

import asyncio
import contextvars
import functools
import io
import logging
import os
import time
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from math import ceil
from typing import Any
from uuid import UUID, uuid4

import crypt4gh.header
import crypt4gh.lib
from crypt4gh.keys import get_private_key
from nacl.bindings import (
    crypto_aead_chacha20poly1305_ietf_decrypt as decrypt_algo,
)
from nacl.bindings import (
    crypto_aead_chacha20poly1305_ietf_encrypt as encrypt_algo,
)
from pydantic import UUID4, SecretBytes

from dhfs.adapters.outbound.http import ConnectionFailedError
from dhfs.config import Config
from dhfs.constants import ENCRYPTION_SECRET_LENGTH, NONCE_LENGTH, SEGMENT_OVERHEAD
from dhfs.core.checksums import Checksums
from dhfs.core.models import FileUpload, InterrogationReport, PartRange
from dhfs.ports.outbound.central import CentralClientPort
from dhfs.ports.outbound.interrogator import InterrogatorPort
from dhfs.ports.outbound.s3 import S3ClientPort
from hexkit.utils import now_utc_ms_prec

log = logging.getLogger(__name__)

# Buffer types the crypto helpers accept. They read through a memoryview, so any
#  contiguous bytes-like object works and no conversion is needed at the call site.
type ByteBuffer = bytes | bytearray | memoryview


@dataclass(frozen=True)
class _PartContext:
    """Everything the per-part helpers need besides the buffers and secrets."""

    file_upload: FileUpload
    part_range: PartRange
    part_no: int
    log_extra: dict
    timings: dict[str, float]

    @property
    def file_id(self) -> UUID4:
        """The ID of the file this part belongs to."""
        return self.file_upload.id


@contextmanager
def _stopwatch(timings: dict[str, float], stage: str) -> Generator[None]:
    """Add the block's elapsed time to `timings[stage]`.

    Deliberately not exception-safe: a stage that raised did not do its work, so its
    time is not recorded.
    """
    start = time.monotonic()
    yield
    timings[stage] += time.monotonic() - start


def _flatten_exception_group(error: BaseException) -> list[BaseException]:
    """Flatten a (possibly nested) ExceptionGroup into a list of leaf exceptions."""
    if isinstance(error, BaseExceptionGroup):
        return [
            leaf
            for child in error.exceptions
            for leaf in _flatten_exception_group(child)
        ]
    return [error]


def _translate_s3_error(error: S3ClientPort.S3Error) -> BaseException:
    """Map an S3 error onto the interrogation error of matching severity."""
    if isinstance(error, S3ClientPort.CriticalS3Error):
        return InterrogatorPort.CriticalError(error)
    return InterrogatorPort.InconclusiveError(error)


def _most_significant_error(group: BaseExceptionGroup) -> BaseException:
    """Pick the error to surface when several parts or files fail concurrently.

    A CriticalError has to stop the whole batch and a ConclusiveError has to fail the
    file outright, so neither may be masked by an InconclusiveError that would merely
    schedule a retry.
    """
    errors = _flatten_exception_group(group)
    for error_type in (
        InterrogatorPort.CriticalError,
        InterrogatorPort.ConclusiveError,
        InterrogatorPort.InconclusiveError,
    ):
        for error in errors:
            if isinstance(error, error_type):
                return error
    return errors[0]


@contextmanager
def _collapsing_error_groups() -> Generator[None]:
    """Reduce a TaskGroup's ExceptionGroup to the single error worth surfacing.

    Only `ExceptionGroup` is caught, never `BaseExceptionGroup`. A group carrying a
    `CancelledError` - or a `KeyboardInterrupt`, or a `SystemExit` - propagates
    untouched, so a concurrent retryable failure can never mask a shutdown signal by
    outranking it.
    """
    try:
        yield
    except ExceptionGroup as group:
        raise _most_significant_error(group) from group


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
        self._max_concurrent_files = config.max_concurrent_files
        self._max_concurrent_parts = config.max_concurrent_parts
        # One budget for every part in flight, shared by all files, so peak memory is
        #  a function of this number alone rather than of it times the file count.
        self._part_slots = asyncio.Semaphore(self._max_concurrent_parts)
        # Crypto and hashing get their own pool rather than the event loop's default
        #  executor, which hexkit's S3 provider uses for every boto3 call. Sharing it
        #  let CPU work squeeze out the S3 round trips this pipeline overlaps it with,
        #  and the default is only min(32, cpu_count + 4) - as few as 5 or 6 workers on
        #  a CPU-limited container. A part never runs more than one of these at a time,
        #  so one worker per part slot is enough.
        self._crypto_executor = ThreadPoolExecutor(
            max_workers=self._max_concurrent_parts, thread_name_prefix="dhfs-crypto"
        )

    def close(self) -> None:
        """Shut the crypto thread pool down. Safe to call more than once."""
        self._crypto_executor.shutdown(wait=False)

    async def _run_crypto(self, func: Callable[..., Any], /, *args, **kwargs) -> Any:
        """Run a blocking crypto/hashing call on the dedicated pool.

        Mirrors `asyncio.to_thread`, including the context propagation, but targets
        `_crypto_executor` instead of the loop's default executor.
        """
        loop = asyncio.get_running_loop()
        context = contextvars.copy_context()
        return await loop.run_in_executor(
            self._crypto_executor, functools.partial(context.run, func, *args, **kwargs)
        )

    async def interrogate_new_files(self) -> None:
        """Query the GHGA Central API for new files that need to be re-encrypted.

        This method handles InterrogationError exceptions by reporting failures to the
        Central API. CantCompleteError exceptions propagate up to the caller.

        Raises:
        - CantCompleteError if an error prevents interrogation from completing (e.g., network issues, S3 unavailable).
        """
        new_files = await self._fetch_batch()
        if new_files is None:
            return

        log.info("Received a batch of %i file(s) to process.", len(new_files))

        semaphore = asyncio.Semaphore(self._max_concurrent_files)

        async def _handle_file(file: FileUpload) -> None:
            """Process one file, absorbing the errors that only concern that file."""
            async with semaphore:
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

        # A CriticalError is not handled above, so it escapes the group and aborts the
        #  remaining files - which is the point, since the batch must not continue.
        with _collapsing_error_groups():
            async with asyncio.TaskGroup() as task_group:
                for file in new_files:
                    task_group.create_task(_handle_file(file))

        log.info("Finished processing current file batch.")

    async def _fetch_batch(self) -> list[FileUpload] | None:
        """Fetch the next batch of files to process.

        Returns None if the batch could not be fetched for a reason that simply calls
        for trying again on the next run.

        Raises:
        - CriticalError if the Central API rejects this version of DHFS.
        """
        try:
            return await self._central_client.fetch_new_uploads()
        except CentralClientPort.UpgradeRequiredError as err:
            raise self.CriticalError(err) from err
        except ConnectionFailedError as err:
            log.error("Unable to reach the GHGA Central API (%s).", str(err))
        except CentralClientPort.CentralAPIError as err:
            log.error("The GHGA Central API returned an error response: %s", err)
        except CentralClientPort.ResponseFormatError as err:
            log.error(
                "The GHGA Central API returned an unrecognized response format: %s", err
            )
        return None

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
        except S3ClientPort.S3Error as err:
            raise _translate_s3_error(err) from err

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

    def _decrypt_part(
        self, *, encrypted_part: ByteBuffer, secret: SecretBytes
    ) -> bytearray:
        """Decrypt an encrypted file part with the given key.

        The output buffer is sized up front: each segment sheds SEGMENT_OVERHEAD bytes.

        Raises DecryptionError if decryption fails or if the input is not framed the
        way that sizing assumes.
        """
        part_size = len(encrypted_part)
        segments = ceil(part_size / crypt4gh.lib.CIPHER_SEGMENT_SIZE)
        key = secret.get_secret_value()
        read_position = write_position = 0

        try:
            # Sizing happens inside the try so that a malformed part fails as a
            #  DecryptionError like any other bad input, rather than escaping as a
            #  bare ValueError that the caller would misread as merely retryable.
            plaintext_size = part_size - SEGMENT_OVERHEAD * segments
            if plaintext_size < 0:
                raise ValueError(
                    f"A part of {part_size} bytes is too short to carry a Crypt4GH"
                    + " nonce and authentication tag"
                )
            buffer = bytearray(plaintext_size)
            source = memoryview(encrypted_part)
            target = memoryview(buffer)
            while read_position < part_size:
                chunk = source[
                    read_position : read_position + crypt4gh.lib.CIPHER_SEGMENT_SIZE
                ]
                # nacl needs real bytes; slicing the view is free.
                decrypted = decrypt_algo(
                    bytes(chunk[NONCE_LENGTH:]),  # data to decrypt (after nonce)
                    None,
                    bytes(chunk[:NONCE_LENGTH]),  # nonce (first 12 bytes)
                    key,
                )
                target[write_position : write_position + len(decrypted)] = decrypted
                write_position += len(decrypted)
                read_position += crypt4gh.lib.CIPHER_SEGMENT_SIZE

            # The buffer is returned whole rather than sliced, since slicing a
            #  bytearray copies it and would undo the point of preallocating. That is
            #  only sound while the segment framing fills it exactly; a short write
            #  would otherwise hand back silent trailing zeros as if they were plaintext.
            if write_position != len(buffer):
                raise ValueError(
                    f"Decryption produced {write_position} bytes for a"
                    + f" {len(buffer)}-byte buffer"
                )
            return buffer
        except Exception as err:
            # We do a catch-all here on purpose - decrypt_algo can raise several error types
            raise self.DecryptionError() from err

    def _reencrypt_part(
        self, *, decrypted_part: ByteBuffer, new_secret: SecretBytes
    ) -> bytes:
        """Re-encrypt a decrypted file part using a new secret.

        Returns `bytes` because the result is handed to httpx, which treats other
        buffer types as iterables of integers.

        May raise exceptions from the underlying encrypt_algo if re-encryption fails.
        """
        part_size = len(decrypted_part)
        segments = ceil(part_size / crypt4gh.lib.SEGMENT_SIZE)
        buffer = bytearray(part_size + SEGMENT_OVERHEAD * segments)
        key = new_secret.get_secret_value()
        read_position = write_position = 0

        source = memoryview(decrypted_part)
        target = memoryview(buffer)
        while read_position < part_size:
            chunk = bytes(
                source[read_position : read_position + crypt4gh.lib.SEGMENT_SIZE]
            )
            nonce = os.urandom(NONCE_LENGTH)
            encrypted = encrypt_algo(chunk, None, nonce, key)
            target[write_position : write_position + NONCE_LENGTH] = nonce
            write_position += NONCE_LENGTH
            target[write_position : write_position + len(encrypted)] = encrypted
            write_position += len(encrypted)
            read_position += crypt4gh.lib.SEGMENT_SIZE

        return bytes(buffer)

    async def _download_part(self, ctx: _PartContext) -> bytes:
        """Download a single encrypted part, translating S3 errors."""
        file_upload = ctx.file_upload
        try:
            with _stopwatch(ctx.timings, "download"):
                return await self._s3_client.fetch_file_content_range(
                    bucket_id=file_upload.bucket_id,
                    object_id=str(file_upload.object_id),
                    start=ctx.part_range.start,
                    stop=ctx.part_range.stop,
                )
        except S3ClientPort.S3Error as err:
            log.warning(
                "File %s: Failed to download part number %i.",
                ctx.file_id,
                ctx.part_no,
                extra=ctx.log_extra,
            )
            raise _translate_s3_error(err) from err

    async def _upload_part(
        self,
        ctx: _PartContext,
        *,
        upload_id: str,
        object_id: str,
        part_md5: bytes,
        part: bytes,
    ) -> None:
        """Upload a single re-encrypted part, translating S3 errors."""
        try:
            with _stopwatch(ctx.timings, "upload"):
                await self._s3_client.upload_file_part(
                    upload_id=upload_id,
                    object_id=object_id,
                    part_no=ctx.part_no,
                    part_md5=part_md5,
                    part=part,
                )
        except S3ClientPort.S3Error as err:
            raise _translate_s3_error(err) from err
        log.debug(
            "File %s: Uploaded S3 part %i.",
            ctx.file_id,
            ctx.part_no,
            extra=ctx.log_extra,
        )

    async def _decrypt_stage(
        self, ctx: _PartContext, *, encrypted_part: ByteBuffer, secret: SecretBytes
    ) -> bytearray:
        """Decrypt a part in a worker thread, keeping the event loop free."""
        try:
            with _stopwatch(ctx.timings, "decrypt"):
                return await self._run_crypto(
                    self._decrypt_part, encrypted_part=encrypted_part, secret=secret
                )
        except Exception as err:
            log.warning(
                "File %s: Failed to decrypt part number %i.",
                ctx.file_id,
                ctx.part_no,
                extra=ctx.log_extra,
            )
            if isinstance(err, (self.InconclusiveError, self.ConclusiveError)):
                raise
            raise self.InconclusiveError(err) from err

    async def _reencrypt_stage(
        self, ctx: _PartContext, *, decrypted_part: ByteBuffer, secret: SecretBytes
    ) -> bytes:
        """Re-encrypt a part under the new secret, in a worker thread."""
        try:
            with _stopwatch(ctx.timings, "reencrypt"):
                return await self._run_crypto(
                    self._reencrypt_part,
                    decrypted_part=decrypted_part,
                    new_secret=secret,
                )
        except Exception as err:
            log.warning(
                "File %s: Failed to re-encrypt a file part.",
                ctx.file_id,
                extra=ctx.log_extra,
            )
            raise self.InconclusiveError(err) from err

    async def _verify_part(
        self, ctx: _PartContext, *, reencrypted_part: ByteBuffer, secret: SecretBytes
    ) -> bytearray:
        """Decrypt a re-encrypted part again to prove the round-trip was lossless.

        This pass is what makes the re-encryption self-checking, so its output - not
        the original plaintext - is what feeds the whole-file checksum.
        """
        try:
            with _stopwatch(ctx.timings, "verify"):
                return await self._run_crypto(
                    self._decrypt_part,
                    encrypted_part=reencrypted_part,
                    secret=secret,
                )
        except Exception as err:
            log.warning(
                "File %s: A file part seems incorrectly re-encrypted.",
                ctx.file_id,
                extra=ctx.log_extra,
            )
            raise self.InconclusiveError(err) from err

    async def _prepare_part(
        self, ctx: _PartContext, *, old_secret: SecretBytes, new_secret: SecretBytes
    ) -> tuple[bytes, tuple[bytes, bytes]]:
        """Produce the bytes to upload for one part, plus their (md5, sha256) digests.

        Each buffer is dropped as soon as the next stage no longer needs it, which
        holds peak memory to the three parts per slot that `max_concurrent_parts`
        documents. The peak is inside the re-encryption: its input, its bytearray
        output, and the `bytes` copy that httpx2 requires are all live at once.
        """
        encrypted_part = await self._download_part(ctx)
        decrypted_part = await self._decrypt_stage(
            ctx, encrypted_part=encrypted_part, secret=old_secret
        )
        del encrypted_part

        reencrypted_part = await self._reencrypt_stage(
            ctx, decrypted_part=decrypted_part, secret=new_secret
        )
        del decrypted_part

        # Digesting a whole part blocks for tens of milliseconds, so it goes to a
        #  thread like the crypto does.
        with _stopwatch(ctx.timings, "digest"):
            part_digests = await self._run_crypto(
                Checksums.digest_encrypted_part, reencrypted_part
            )
        return reencrypted_part, part_digests

    async def _process_file_parts(
        self,
        *,
        file_upload: FileUpload,
        new_object_id: str,
        upload_id: str,
        old_secret: SecretBytes,
        new_secret: SecretBytes,
    ) -> Checksums:
        """Perform the decrypt/re-encrypt/decrypt/upload cycle on each file part.

        Parts are processed with bounded concurrency so the download of one part
        overlaps the CPU work of another and the upload of a third, and within a part
        the verify pass overlaps the upload. Crypto and hashing run in worker threads
        to keep the event loop free for that overlap.

        Returns the `Checksums` object containing the checksums calculated during
        the file processing. All error translation is done here, but all S3 cleanup is
        handled from the calling function, `interrogate_file()`.

        Raises:
        - DecryptionError if a file part cannot be decrypted.
        - InconclusiveError if a part cannot be downloaded, re-encrypted or uploaded.
        - CriticalError if S3 reports a problem that stops the whole batch.
        """
        checksums = Checksums()
        file_id = file_upload.id
        inbox_object_id = str(file_upload.object_id)
        part_ranges = list(file_upload.calc_encrypted_part_ranges())

        # The whole-file sha256 is order-dependent, so each part waits for its
        #  predecessor to be folded in before folding itself in and releasing the next.
        hashed: list[asyncio.Event] = [asyncio.Event() for _ in part_ranges]

        timings = dict.fromkeys(
            ("download", "decrypt", "reencrypt", "verify", "digest", "fold", "upload"),
            0.0,
        )

        async def _handle_part(
            index: int, part_range: PartRange
        ) -> tuple[bytes, bytes]:
            """Process one part, returning its (md5, sha256) digests."""
            part_no = index + 1

            # Acquisition is FIFO and tasks are created in part order, so a part is
            #  never admitted ahead of its predecessor. That is what keeps the fold
            #  chain below deadlock-free: it only ever waits on an admitted part.
            async with self._part_slots:
                log.debug("File %s: Processing part %s.", file_id, part_no)
                ctx = _PartContext(
                    file_upload=file_upload,
                    part_range=part_range,
                    part_no=part_no,
                    log_extra={  # only for logging purposes
                        "file_id": file_id,
                        "inbox_object_id": inbox_object_id,
                        "reencrypted_object_id": new_object_id,
                        "file_part_number": part_no,
                        "content_range": f"{part_range.start}-{part_range.stop}",
                    },
                    timings=timings,
                )

                reencrypted_part, part_digests = await self._prepare_part(
                    ctx, old_secret=old_secret, new_secret=new_secret
                )

                async def _verify_and_fold(part: bytes) -> None:
                    """Prove the round-trip, then fold the plaintext into the file hash."""
                    verified_part = await self._verify_part(
                        ctx, reencrypted_part=part, secret=new_secret
                    )
                    # Waiting here rather than after the upload keeps the chain
                    #  advancing at crypto speed, not S3 speed. The successor stays
                    #  blocked until the threaded fold returns, so order still holds.
                    if index:
                        await hashed[index - 1].wait()
                    with _stopwatch(timings, "fold"):
                        await self._run_crypto(
                            checksums.update_unencrypted, verified_part
                        )
                    hashed[index].set()

                # The verify pass feeds the whole-file checksum but nothing the upload
                #  needs, so the two run together rather than in sequence.
                async with asyncio.TaskGroup() as part_group:
                    part_group.create_task(_verify_and_fold(reencrypted_part))
                    part_group.create_task(
                        self._upload_part(
                            ctx,
                            upload_id=upload_id,
                            object_id=new_object_id,
                            part_md5=part_digests[0],
                            part=reencrypted_part,
                        )
                    )

                # Free the buffer before the next part takes this slot
                del reencrypted_part
                return part_digests

        _wall = time.monotonic()
        with _collapsing_error_groups():
            async with asyncio.TaskGroup() as task_group:
                tasks = [
                    task_group.create_task(_handle_part(index, part_range))
                    for index, part_range in enumerate(part_ranges)
                ]
        wall_time = time.monotonic() - _wall

        checksums.set_encrypted_parts([task.result() for task in tasks])

        self._log_part_metrics(
            file_upload=file_upload,
            part_count=len(part_ranges),
            timings=timings,
            wall_time=wall_time,
        )
        return checksums

    def _log_part_metrics(
        self,
        *,
        file_upload: FileUpload,
        part_count: int,
        timings: dict[str, float],
        wall_time: float,
    ) -> None:
        """Log throughput metrics for a completed file."""
        size_mib = file_upload.decrypted_size / (1024**2)

        def _throughput(elapsed: float) -> int:
            return round(size_mib / elapsed) if elapsed > 0 else 0

        metrics: dict[str, float | int] = {
            "part_count": part_count,
            "max_concurrent_parts": self._max_concurrent_parts,
        }
        for stage, elapsed in timings.items():
            metrics[f"{stage}_s"] = round(elapsed, 3)
            metrics[f"{stage}_mib_per_s"] = _throughput(elapsed)

        # Stage times are summed across parts and overlap each other, so only wall
        #  time reflects how long the file actually took.
        metrics["stage_total_s"] = round(sum(timings.values()), 3)
        metrics["total_s"] = round(wall_time, 3)
        metrics["total_mib_per_s"] = _throughput(wall_time)

        log.info(
            "File %s: Re-encryption process complete. See log details for metrics.",
            file_upload.id,
            extra=metrics,
        )

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
        except S3ClientPort.S3Error as err:
            raise _translate_s3_error(err) from err

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
