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

"""Models for objects in the DHFS"""

import logging
from collections.abc import Generator
from dataclasses import dataclass
from functools import cached_property
from math import ceil

import crypt4gh.lib
from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, BaseModel, Field, SecretBytes, computed_field

from dhfs.constants import AUTH_TAG_LENGTH, NONCE_LENGTH

__all__ = ["FileUpload", "InterrogationReport", "PartRange"]


log = logging.getLogger(__name__)


@dataclass
class PartRange:
    """Container for download ranges"""

    start: int
    stop: int


class FileUpload(BaseModel):
    """Represents a file that needs to be interrogated and re-encrypted"""

    id: UUID4 = Field(default=..., description="The unique identifier of the file")
    storage_alias: str = Field(
        default=...,
        description="The storage alias indicating the data hub the file is housed at",
    )
    bucket_id: str = Field(
        default=...,
        description="The name of the inbox bucket from which DHFS should fetch the file",
    )
    object_id: UUID4 = Field(
        default=..., description="The ID of the file object in the inbox bucket."
    )
    decrypted_sha256: str = Field(
        default=..., description="The SHA256 checksum of the unencrypted file content."
    )
    decrypted_size: int = Field(
        default=..., description="The size of the unencrypted file content."
    )
    encrypted_size: int = Field(
        default=...,
        description=(
            "The size of the encrypted file content. When in the inbox, this"
            + " includes the Crypt4GH envelope. Once interrogated, the size is reduced"
            + " because the encrypted content no longer contains the envelope."
        ),
    )
    part_size: int = Field(
        default=...,
        description="The part size used by the submitter when uploading this file.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def offset(self) -> int:
        """Calculate the size of the file encryption envelope/where content begins"""
        # The number of encrypted chunks produced during encryption depends on the file
        #  size. ChaCha20Poly1305 encrypts SEGMENT_SIZE bytes at a time
        chunks = self.decrypted_size // crypt4gh.lib.SEGMENT_SIZE

        # Each full-length encrypted chunk in the file is CIPHER_SEGMENT_SIZE bytes long
        # The difference is 28 bytes. This comes from a 12-byte NONCE and a 16-byte auth tag.
        chunk_size = crypt4gh.lib.CIPHER_SEGMENT_SIZE

        # The last bytes of the file, which are less than SEGMENT_SIZE, are encrypted as
        #  is - no magic padding. So if there are 40 straggler bytes, it's 68 when encrypted.
        unencrypted_remainder = self.decrypted_size - crypt4gh.lib.SEGMENT_SIZE * chunks
        size_sans_envelope = chunk_size * chunks
        if unencrypted_remainder:
            size_sans_envelope += unencrypted_remainder + NONCE_LENGTH + AUTH_TAG_LENGTH

        # We can therefore calculate the encrypted file size given the decrypted size,
        #  and use that to calculate the size of the envelope / offset of the content.
        return self.encrypted_size - size_sans_envelope

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def adjusted_part_size(self) -> int:
        """Calculate the adjusted part size which is both evenly divisible by
        the cipher segment size and ensures the file will contain < 10000 parts (the S3
        limit for multipart uploads). This ensures we download complete segments that
        can be decrypted.
        """
        segments_per_part = ceil(self.part_size / crypt4gh.lib.CIPHER_SEGMENT_SIZE)
        adjusted_part_size = segments_per_part * crypt4gh.lib.CIPHER_SEGMENT_SIZE

        # If the adjusted size would result in hitting 10k parts, we need to increase
        #  the part size to bring that below the 10k threshold (we'll shoot for 9995)
        if ceil(self.encrypted_size / adjusted_part_size) >= 10_000:
            # Get a part size that breaks the encrypted content into 9995 parts, then
            #  divide evenly by CIPHER_SEGMENT_SIZE
            new_part_size = ceil((self.encrypted_size - self.offset) / 9_995)

            # Bring into alignment again, rounding part size up since we're trying to
            #  keep total part count down and it's already near the limit
            segments_per_part = ceil(new_part_size / crypt4gh.lib.CIPHER_SEGMENT_SIZE)
            adjusted_part_size = segments_per_part * crypt4gh.lib.CIPHER_SEGMENT_SIZE

        if adjusted_part_size != self.part_size:
            log.debug(
                "File %s: Adjusted part size %s from %d to %d bytes to align with Crypt4GH"
                + " segment boundaries.",
                self.id,
                "down" if adjusted_part_size < self.part_size else "up",
                self.part_size,
                adjusted_part_size,
            )
        return adjusted_part_size

    def calc_encrypted_part_ranges(self) -> Generator[PartRange]:
        """Calculate file part ranges that align with the Crypt4GH segment size"""
        processed = self.offset
        while processed < self.encrypted_size:
            start = processed
            processed += self.adjusted_part_size
            end = min(processed, self.encrypted_size)
            yield PartRange(start, end)


class InterrogationReport(BaseModel):
    """Model representing the outcome of a file interrogation"""

    file_id: UUID4 = Field(..., description="The unique identifier of the file")
    storage_alias: str = Field(
        default=...,
        description="The storage alias indicating the data hub the file is housed at",
    )
    bucket_id: str | None = Field(
        default=None,
        description=(
            "The name of the interrogation bucket the file is stored"
            + " in, if interrogation was successful"
        ),
    )
    object_id: UUID4 | None = Field(
        default=None,
        description=(
            "The ID of the file specific to its S3 bucket, if the interrogation was"
            + " successful."
        ),
    )
    interrogated_at: UTCDatetime = Field(
        default=..., description="The time interrogation occurred."
    )
    passed: bool = Field(
        default=..., description="Whether or not interrogation was successful."
    )
    secret: SecretBytes | None = Field(
        default=None, description="The base64-encoded encrypted file encryption secret."
    )
    encrypted_parts_md5: list[str] | None = Field(
        default=None,
        description=(
            "A list of the MD5 checksums converted from digest bytes to hex"
            + " string representation"
        ),
    )
    encrypted_parts_sha256: list[str] | None = Field(
        default=None,
        description=(
            "A list of the SHA256 checksums converted from digest bytes to hex"
            + " string representation"
        ),
    )
    encrypted_size: int | None = Field(
        default=None,
        description=(
            "The size of the encrypted file content without envelope, if interrogation"
            + " is successful."
        ),
    )
    reason: str | None = Field(
        default=None, description="The reason the file interrogation failed."
    )
