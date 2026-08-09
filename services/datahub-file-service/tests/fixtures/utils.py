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

"""Utils for Fixture handling."""

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import crypt4gh.header
import crypt4gh.lib
import httpx2
from crypt4gh.keys import get_private_key, get_public_key
from ghga_service_commons.utils import jwt_helpers
from ghga_service_commons.utils.crypt import encode_key, generate_key_pair
from ghga_service_commons.utils.temp_files import big_temp_file
from hexkit.providers.s3.provider import S3ObjectStorage
from nacl.bindings import (
    crypto_aead_chacha20poly1305_ietf_encrypt as encrypt_algo,
)
from pydantic import SecretBytes, SecretStr

from dhfs.constants import ENCRYPTION_SECRET_LENGTH, NONCE_LENGTH
from dhfs.core.checksums import Checksums
from dhfs.core.models import FileUpload

BASE_DIR = Path(__file__).parent.resolve()
DHFS_CRYPT4GH_PRIVATE_KEY_PATH = BASE_DIR / "keys/dhfs_key.sec"
DHFS_CRYPT4GH_PUBLIC_KEY_PATH = BASE_DIR / "keys/dhfs_key.pub"
DHFS_JWK = jwt_helpers.generate_jwk()
DHFS_SIGNING_KEY = DHFS_JWK.export_private()
CENTRAL_CRYPT4GH_KEYPAIR = generate_key_pair()
CENTRAL_CRYPT4GH_PUBLIC_KEY = encode_key(CENTRAL_CRYPT4GH_KEYPAIR.public)
CENTRAL_CRYPT4GH_PRIVATE_KEY = encode_key(CENTRAL_CRYPT4GH_KEYPAIR.private)
INBOX = "inbox1"


@dataclass
class EncryptedObject:
    """Test object with random data encrypted using an abbreviated version of the
    real encryption process
    """

    checksums: Checksums
    unencrypted_size: int
    encrypted_size: int
    part_size: int
    offset: int
    data: bytes


async def upload_dummy_data(
    *,
    bucket_id: str,
    object_id: str,
    storage: S3ObjectStorage,
    content: bytes | None = None,
):
    """Upload dummy data to the S3 storage for a given bucket and object ID"""
    content = content or b"this is some object content. " * 2000
    upload_id = await storage.init_multipart_upload(
        bucket_id=bucket_id, object_id=object_id
    )
    url = await storage.get_part_upload_url(
        upload_id=upload_id, bucket_id=bucket_id, object_id=object_id, part_number=1
    )
    httpx2.put(url, content=content)
    await storage.complete_multipart_upload(
        upload_id=upload_id, bucket_id=bucket_id, object_id=object_id
    )


def get_crypt4gh_private_key(
    key_path: Path = DHFS_CRYPT4GH_PRIVATE_KEY_PATH, passphrase: SecretStr | None = None
) -> SecretBytes:
    """Get the crypt4gh private key stored in the specified path"""

    def callback():
        return passphrase.get_secret_value() if passphrase else None

    return SecretBytes(get_private_key(key_path, callback))


def _make_envelope(
    file_secret: bytes, public_key_path: Path = DHFS_CRYPT4GH_PUBLIC_KEY_PATH
) -> bytes:
    submitter_private_key = generate_key_pair().private
    keys = [(0, submitter_private_key, get_public_key(public_key_path))]
    header_content = crypt4gh.header.make_packet_data_enc(0, file_secret)
    header_packets = crypt4gh.header.encrypt(header_content, keys)
    return crypt4gh.header.serialize(header_packets)


def get_encrypted_object(
    part_size: int,
    file_size: int = (10 * 1024**2),
    public_key_path: Path = DHFS_CRYPT4GH_PUBLIC_KEY_PATH,
) -> EncryptedObject:
    """Generate an ID, encryption secret, etc. to provide actual encrypted data
    for testing.
    """
    file_secret = os.urandom(ENCRYPTION_SECRET_LENGTH)
    checksums = Checksums()
    envelope = _make_envelope(file_secret=file_secret, public_key_path=public_key_path)
    encrypted_data = envelope

    # Encrypt data in Crypt4GH SEGMENT_SIZE chunks, not part_size chunks
    with big_temp_file(file_size) as file:
        unencrypted_size = file.tell()
        file.seek(0)
        while unencrypted_chunk := file.read(crypt4gh.lib.SEGMENT_SIZE):
            checksums.update_unencrypted(unencrypted_chunk)
            nonce = os.urandom(NONCE_LENGTH)
            encrypted_chunk = encrypt_algo(unencrypted_chunk, None, nonce, file_secret)
            encrypted_data += nonce + encrypted_chunk

    # Iterate through encrypted data and calculate checksums on encrypted content
    for i in range((len(encrypted_data) // part_size) + 1):
        part = encrypted_data[i * part_size : (i + 1) * part_size]
        if part:
            checksums.update_encrypted(part)

    return EncryptedObject(
        checksums=checksums,
        unencrypted_size=unencrypted_size,
        encrypted_size=len(encrypted_data),
        part_size=part_size,
        offset=len(envelope),
        data=encrypted_data,
    )


async def upload_encrypted_object(
    *,
    bucket_id: str,
    object_id: str,
    storage: S3ObjectStorage,
    encrypted_object: EncryptedObject,
):
    """Upload dummy data to the S3 storage for a given bucket and object ID"""
    upload_id = await storage.init_multipart_upload(
        bucket_id=bucket_id, object_id=object_id
    )
    for i in range(len(encrypted_object.checksums.encrypted_md5)):
        start = i * encrypted_object.part_size
        stop = (i + 1) * encrypted_object.part_size
        content = encrypted_object.data[start:stop]
        url = await storage.get_part_upload_url(
            upload_id=upload_id,
            bucket_id=bucket_id,
            object_id=object_id,
            part_number=i + 1,
        )
        httpx2.put(url, content=content)
    await storage.complete_multipart_upload(
        upload_id=upload_id, bucket_id=bucket_id, object_id=object_id
    )


def make_file_upload(
    decrypted_size: int, encrypted_size: int, part_size: int = 5 * 1024**2
) -> FileUpload:
    """Make a FileUpload instance using the provided attributes."""
    return FileUpload(
        id=uuid4(),
        storage_alias="TUE01",
        bucket_id=INBOX,
        object_id=uuid4(),
        decrypted_sha256="test",
        decrypted_size=decrypted_size,
        encrypted_size=encrypted_size,
        part_size=part_size,
    )
