# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Defines dataclasses for holding business-logic data"""

from pydantic import BaseModel, Field


class FileMetadataBase(BaseModel):
    """A model containing metadata on a registered file."""

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )
    upload_date: str = Field(
        ...,
        description="The date and time when this file was ingested into the system.",
    )
    decrypted_size: int = Field(
        ...,
        description="The size of the entire decrypted file content in bytes.",
    )
    decryption_secret_id: str = Field(
        ...,
        description=(
            "The ID of the symmetic file encryption/decryption secret."
            + " Please note, this is not the secret itself."
        ),
    )
    content_offset: int = Field(
        ...,
        description=(
            "The offset in bytes at which the encrypted content starts (excluding the"
            + " crypt4GH envelope)."
        ),
    )
    encrypted_part_size: int = Field(
        ...,
        description=(
            "The size of the file parts of the encrypted content (excluding the"
            + " crypt4gh envelope) as used for the encrypted_parts_md5 and the"
            + " encrypted_parts_sha256 in bytes. The same part size is recommended for"
            + " moving that content."
        ),
    )
    encrypted_parts_md5: list[str] = Field(
        ...,
        description=(
            "MD5 checksums of file parts of the encrypted content (excluding the"
            + " crypt4gh envelope)."
        ),
    )
    encrypted_parts_sha256: list[str] = Field(
        ...,
        description=(
            "SHA-256 checksums of file parts of the encrypted content (excluding the"
            + " crypt4gh envelope)."
        ),
    )
    decrypted_sha256: str = Field(
        ...,
        description="The SHA-256 checksum of the entire decrypted file content.",
    )
    storage_alias: str = Field(
        ...,
        description="Alias for the object storage location where the given object is stored.",
    )


class FileMetadata(FileMetadataBase):
    """The file metadata plus a object storage ID generated upon registration"""

    object_id: str = Field(
        ..., description="A UUID to identify the file in object storage"
    )
