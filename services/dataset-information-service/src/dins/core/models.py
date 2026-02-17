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
"""Models for internal representation"""

from typing import Annotated

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, BaseModel, Field, PositiveInt, StringConstraints


class FileAccession(BaseModel):
    """Public identifier for one file information object.

    Represents not-yet-populated or already deleted file information objects.
    """

    accession: str = Field(
        default=...,
        description="Public identifier of the file associated with the given information",
    )


class FileInformation(FileAccession):
    """Public information for files registered with the Internal File Registry service."""

    size: PositiveInt = Field(
        default=..., description="Size of the unencrypted file in bytes."
    )
    sha256_hash: str = Field(
        default=...,
        description="SHA256 hash of the unencrypted file content encoded as hexadecimal"
        " values as produced by hashlib.hexdigest().",
    )
    storage_alias: str = Field(
        default=...,
        description="Alias of the storage location where the corresponding file data resides"
        " in permanent storage.",
    )


class DatasetFileAccessions(BaseModel):
    """The accession of a dataset and the accessions of all its files."""

    accession: str = Field(default=..., description="Public accession of a dataset.")
    file_accessions: list[str] = Field(
        default=...,
        description="Public accessions for all files included in the corresponding dataset.",
    )


class DatasetFileInformation(BaseModel):
    """Public information for a dataset."""

    accession: str = Field(default=..., description="Public accession of a dataset.")
    file_information: list[FileAccession | FileInformation] = Field(
        default=...,
        description="Public information on all files belonging to a dataset or only the accession,"
        " if no detailed information is available.",
    )


Accession = Annotated[str, StringConstraints(pattern=r"^GHGA.+")]


class FileInternallyRegistered(BaseModel):
    """An event schema communicating that a file has been copied into permanent storage.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """

    file_id: UUID4 = Field(..., description="Unique identifier for the file upload")
    accession: Accession = Field(
        default=..., description="The accession number assigned to this file."
    )
    archive_date: UTCDatetime = Field(
        ...,
        description="The date and time when this file was archived.",
    )
    storage_alias: str = Field(
        default=..., description="The storage alias of the Data Hub housing the file"
    )
    bucket_id: str = Field(
        ..., description="The ID/name of the S3 bucket used to store the file."
    )
    secret_id: str = Field(
        default=..., description="The ID of the file decryption secret."
    )
    decrypted_size: int = Field(..., description="The size of the unencrypted file")
    encrypted_size: int = Field(
        default=..., description="The encrypted size of the file before re-encryption"
    )
    decrypted_sha256: str = Field(
        default=...,
        description="SHA-256 checksum of the entire unencrypted file content",
    )
    encrypted_parts_md5: list[str] = Field(
        default=..., description="The MD5 checksum of each encrypted file part"
    )
    encrypted_parts_sha256: list[str] = Field(
        default=..., description="The SHA-256 checksum of each encrypted file part"
    )
    part_size: int = Field(
        default=...,
        description="The number of bytes in each file part (last part is likely smaller)",
    )
