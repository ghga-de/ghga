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

"""Logic for verifying DHFS functionality"""

import hashlib
import logging
import os
from collections.abc import Callable, Generator
from contextlib import suppress
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID

import crypt4gh.header
import crypt4gh.lib
from crypt4gh.keys import get_private_key, get_public_key
from nacl.bindings import (
    crypto_aead_chacha20poly1305_ietf_encrypt as encrypt_algo,
)
from pydantic import SecretBytes, SecretStr

from dhfs.adapters.outbound.central import CentralClient
from dhfs.adapters.outbound.http import get_configured_httpx_client
from dhfs.config import Config
from dhfs.constants import ENCRYPTION_SECRET_LENGTH, NONCE_LENGTH
from dhfs.core import models
from dhfs.inject import prepare_interrogator
from ghga_service_commons.utils.crypt import generate_key_pair
from hexkit.providers.s3 import S3Config
from hexkit.providers.s3.provider import S3ObjectStorage

__all__ = ["run_dhfs_verification"]

log = logging.getLogger(__name__)

FILE_ID = UUID("00000000-0000-4000-b000-000000000000")

# Fixed object ID used in the inbox bucket during verification.
OBJECT_ID_UUID = UUID("00000000-0000-4000-b000-000000000001")
OBJECT_ID_STR = str(OBJECT_ID_UUID)

# Fixed object ID injected into the interrogator so cleanup can locate the
# re-encrypted file by a known ID rather than a runtime-generated UUID.
INTERROGATION_OBJECT_ID = UUID("00000000-0000-4000-b000-000000000002")
SUBMITTER_SECRET = os.urandom(ENCRYPTION_SECRET_LENGTH)
PART_SIZE = 64 * 1024**2  # 64 MiB


async def run_dhfs_verification(config: Config, *, file_size: int):
    """Use dummy data and mock FIS responses in order to verify DHFS compatibility
    with the current S3 backend. This is useful as a smoke test.
    """
    _validate_config_for_verifier(config)

    inbox_write_storage = _get_inbox_storage_with_write_access(config)
    normal_dhfs_storage = S3ObjectStorage(config=config)

    log.info("Checking that required S3 buckets exist...")
    await _assert_bucket_exists(
        storage=inbox_write_storage,
        bucket_id=config.inbox_bucket_id,  # type: ignore[arg-type]
        label="inbox",
        credential_note="temporary inbox write-access",
    )
    await _assert_bucket_exists(
        storage=normal_dhfs_storage,
        bucket_id=config.interrogation_bucket_id,
        label="interrogation",
        credential_note="normal DHFS",
    )

    # Ping the Central API to make sure DHFS version is outdated
    async with get_configured_httpx_client(config=config) as httpx_client:
        central_client = CentralClient(config=config, httpx_client=httpx_client)
        log.debug("Checking if DHFS version is accepted by Central.")
        _ = await central_client.fetch_new_uploads()
    log.info("Verified that DFHS version is accepted by Central.")

    log.info("Checking for lingering data from any prior runs.")
    try:
        await _clean_buckets(
            config=config,
            inbox_write_storage=inbox_write_storage,
            dhfs_storage=normal_dhfs_storage,
        )

        file_upload = await _upload_inbox_dummy_file(
            config=config,
            inbox_write_storage=inbox_write_storage,
            public_key_path=config.data_hub_crypt4gh_public_key_path,  # type: ignore
            file_size=file_size,
        )
    except Exception as err:
        log.error(err)
        return

    # Patch uuid4 so the re-encrypted object ID is set to INTERROGATION_OBJECT_ID. That
    #  lets us find it more easily. Central hands out the dummy file as a batch of one,
    #  and the report DHFS would send it is kept by the mock instead.
    with (
        patch.object(
            CentralClient,
            "fetch_new_uploads",
            new_callable=AsyncMock,
            return_value=[file_upload],
        ),
        patch.object(
            CentralClient, "submit_interrogation_report", new_callable=AsyncMock
        ) as submit_report,
        patch("dhfs.core.interrogator.uuid4", return_value=INTERROGATION_OBJECT_ID),
    ):
        log.info("Performing DHFS file processing.")
        async with prepare_interrogator(config=config) as interrogator:
            try:
                await interrogator.interrogate_new_files()
                _check_report(submit_report)
                log.info("File processing succeeded.")
            except Exception as err:
                raise RuntimeError(f"File processing failed: {err!s}") from err
            finally:
                log.info("Performing cleanup.")
                await _clean_buckets(
                    config=config,
                    inbox_write_storage=inbox_write_storage,
                    dhfs_storage=normal_dhfs_storage,
                )


def _check_report(submit_report: AsyncMock) -> None:
    """Raise unless DHFS reported the dummy file as successfully processed.

    No report means the attempt was inconclusive; DHFS logged why as a warning.
    """
    if not submit_report.await_args:
        raise RuntimeError("DHFS could not process the file conclusively.")
    report: models.InterrogationReport = submit_report.await_args.kwargs["report"]
    if not report.passed:
        raise RuntimeError(report.reason or "DHFS reported the file as failed.")


def _validate_config_for_verifier(config: Config):
    """Ensure the optional fields in the config, which are actually required for the
    verifier functionality, are set.
    """
    if not config.data_hub_crypt4gh_public_key_path:
        raise ValueError("data_hub_crypt4gh_public_key_path must be configured.")
    if not config.inbox_bucket_id:
        raise ValueError("inbox_bucket_id must be configured.")
    if not config.inbox_write_s3_access_key_id:
        raise ValueError("inbox_write_s3_access_key_id must be configured.")
    if not config.inbox_write_s3_secret_access_key:
        raise ValueError("inbox_write_s3_secret_access_key must be configured.")


def _get_inbox_storage_with_write_access(config: Config) -> S3ObjectStorage:
    """Construct an S3ObjectStorage using the write-capable inbox credentials.

    The S3 endpoint is shared with the main config; only the credentials differ.
    """
    inbox_write_s3_config = S3Config(
        s3_endpoint_url=config.s3_endpoint_url,
        s3_access_key_id=config.inbox_write_s3_access_key_id,
        s3_secret_access_key=config.inbox_write_s3_secret_access_key,
        s3_session_token=config.inbox_write_s3_session_token,
    )
    return S3ObjectStorage(config=inbox_write_s3_config)


async def _assert_bucket_exists(
    *,
    storage: S3ObjectStorage,
    bucket_id: str,
    label: str,
    credential_note: str,
) -> None:
    """Raise ValueError with an actionable message if the bucket does not exist."""
    if not await storage.does_bucket_exist(bucket_id):
        raise ValueError(
            f"The {label} bucket '{bucket_id}' does not exist."
            f" Create the bucket before running verify"
            f" ({credential_note} credentials were used for this check)."
        )


async def _clean_buckets(
    config: Config,
    inbox_write_storage: S3ObjectStorage,
    dhfs_storage: S3ObjectStorage,
):
    """Delete the dummy objects from the buckets if applicable, along with any
    multipart uploads.
    """
    for bucket_id, object_id, storage in [
        (config.inbox_bucket_id, OBJECT_ID_STR, inbox_write_storage),
        (config.interrogation_bucket_id, str(INTERROGATION_OBJECT_ID), dhfs_storage),
    ]:
        if not bucket_id:  # These should be set, but type checker doesn't know that
            raise RuntimeError(
                "Both inbox_bucket_id and interrogation_bucket_id must be configured."
            )

        try:
            uploads = await storage.list_multipart_uploads_for_object(
                bucket_id=bucket_id,
                object_id=object_id,
            )
            for upload_id in uploads:
                await storage.abort_multipart_upload(
                    upload_id=upload_id,
                    bucket_id=bucket_id,
                    object_id=object_id,
                )
            if uploads:
                log.info(
                    "Aborted %i multipart upload(s) for the dummy file in"
                    " the %s bucket.",
                    len(uploads),
                    bucket_id,
                )

            with suppress(S3ObjectStorage.ObjectNotFoundError):
                await storage.delete_object(
                    bucket_id=bucket_id,
                    object_id=object_id,
                )
                log.info("Deleted dummy object from the %s bucket.", bucket_id)
        except Exception as err:
            raise RuntimeError(
                f"Could not remove dummy data from the {bucket_id} bucket: {err!s}"
            ) from err


async def _upload_inbox_dummy_file(
    *,
    config: Config,
    inbox_write_storage: S3ObjectStorage,
    public_key_path: Path,
    file_size: int,
    part_size: int = PART_SIZE,
) -> models.FileUpload:
    """Generate a fresh encrypted dummy file and upload it to the inbox."""
    envelope = _make_envelope(
        file_secret=SUBMITTER_SECRET, public_key_path=public_key_path
    )
    log.info(
        "Uploading %i MiB of encrypted dummy data in parts of %i bytes...",
        file_size // 1024**2,
        part_size,
    )
    try:
        decrypted_sha256, encrypted_size = await _upload_dummy_data(
            config=config,
            storage=inbox_write_storage,
            envelope=envelope,
            file_size=file_size,
            part_size=part_size,
        )
    except Exception as err:
        raise RuntimeError(
            f"Failed to upload the dummy file to the {config.inbox_bucket_id} bucket: {err!s}"
        ) from err

    # DHFS aligns the part size to whole Crypt4GH segments itself
    return models.FileUpload(
        id=FILE_ID,
        object_id=OBJECT_ID_UUID,
        storage_alias=config.storage_alias,
        bucket_id=config.inbox_bucket_id,
        decrypted_sha256=decrypted_sha256,
        decrypted_size=file_size,
        encrypted_size=encrypted_size,
        part_size=part_size,
    )


def _encrypted_dummy_parts(
    *,
    file_size: int,
    part_size: int,
    envelope: bytes,
    hash_plaintext: Callable[[bytes], None],
) -> Generator[bytes]:
    """Generate random data, encrypt it and yield the object it makes, part by part.

    Only one part is held at a time, so memory does not grow with the file size.
    Each plaintext segment is passed to `hash_plaintext`.
    """
    pending = bytearray(envelope)
    remaining = file_size
    while remaining:
        segment = os.urandom(min(crypt4gh.lib.SEGMENT_SIZE, remaining))
        remaining -= len(segment)
        hash_plaintext(segment)
        nonce = os.urandom(NONCE_LENGTH)
        pending += nonce + encrypt_algo(segment, None, nonce, SUBMITTER_SECRET)
        while len(pending) >= part_size:
            yield bytes(pending[:part_size])
            del pending[:part_size]
    if pending:
        yield bytes(pending)


async def _upload_dummy_data(
    *,
    config: Config,
    storage: S3ObjectStorage,
    envelope: bytes,
    file_size: int,
    part_size: int,
) -> tuple[str, int]:
    """Upload a fresh encrypted dummy file to the inbox bucket, a part as it is made.

    Returns the SHA-256 of the plaintext and the size of the encrypted object.
    """
    inbox_bucket_id = config.inbox_bucket_id

    if not inbox_bucket_id:
        raise RuntimeError("Config parameter inbox_bucket_id must be set.")

    plaintext_sha256 = hashlib.sha256()
    upload_id = await storage.init_multipart_upload(
        bucket_id=inbox_bucket_id, object_id=OBJECT_ID_STR
    )

    encrypted_size = 0
    async with get_configured_httpx_client(config=config) as client:
        parts = _encrypted_dummy_parts(
            file_size=file_size,
            part_size=part_size,
            envelope=envelope,
            hash_plaintext=plaintext_sha256.update,
        )
        for part_number, content in enumerate(parts, start=1):
            log.info("Uploading part number %i.", part_number)
            # The upload was created just above, so checking it per part is wasted
            url = await storage.get_part_upload_url(
                upload_id=upload_id,
                bucket_id=inbox_bucket_id,
                object_id=OBJECT_ID_STR,
                part_number=part_number,
                expires_after=300,
                verify_upload=False,
            )

            response = await client.put(url, content=content, timeout=300)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Inbox part upload returned HTTP {response.status_code}."
                    f" Response: {response.text}"
                )
            encrypted_size += len(content)
    await storage.complete_multipart_upload(
        upload_id=upload_id, bucket_id=inbox_bucket_id, object_id=OBJECT_ID_STR
    )
    return plaintext_sha256.hexdigest(), encrypted_size


def _make_envelope(file_secret: bytes, public_key_path: Path) -> bytes:
    submitter_private_key = generate_key_pair().private
    keys = [(0, submitter_private_key, get_public_key(public_key_path))]
    header_content = crypt4gh.header.make_packet_data_enc(0, file_secret)
    header_packets = crypt4gh.header.encrypt(header_content, keys)
    return crypt4gh.header.serialize(header_packets)


def _get_crypt4gh_private_key(
    key_path: Path, passphrase: SecretStr | None = None
) -> SecretBytes:
    """Get the crypt4gh private key stored in the specified path"""

    def callback():
        return passphrase.get_secret_value() if passphrase else None

    return SecretBytes(get_private_key(key_path, callback))
