# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from pydantic import BaseModel, Field, PositiveInt


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
