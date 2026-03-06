# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Defines dataclasses for business-logic data as well as request/reply models for use
in the api.
"""

import re
from typing import Literal

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator


class AccessURL(BaseModel):
    """AccessUrl object for access method"""

    url: str


class AccessMethod(BaseModel):
    """Wrapped DRS access_methods field value"""

    access_url: AccessURL
    type: Literal["s3"] = "s3"


class Checksum(BaseModel):
    """Wrapped DRS checksums field value"""

    checksum: str
    type: Literal["sha-256"] = "sha-256"


class DrsObjectBase(BaseModel):
    """A model containing the metadata needed to register a new DRS object."""

    file_id: UUID4
    secret_id: str
    decrypted_sha256: str
    decrypted_size: int
    encrypted_size: int
    creation_date: UTCDatetime
    storage_alias: str


class DrsObject(DrsObjectBase):
    """A DrsObjectBase with the object_id generated"""

    object_id: UUID4  # the S3 object ID as uuid4


class AccessTimeDrsObject(DrsObject):
    """DRS Model with information for outbox caching strategy"""

    last_accessed: UTCDatetime


class DrsObjectWithUri(DrsObject):
    """A model for describing DRS object metadata including a self URI."""

    self_uri: str


class DrsObjectWithAccess(DrsObject):
    """A model for describing DRS object metadata including information on how to access
    its content.
    """

    access_url: str

    def convert_to_drs_response_model(
        self, size: int, drs_server_uri_base: str, accession: str
    ):
        """Convert from internal representation ingested by even to DRS compliant representation"""
        access_method = AccessMethod(access_url=AccessURL(url=self.access_url))
        checksum = Checksum(checksum=self.decrypted_sha256)

        return DrsObjectResponseModel(
            access_methods=[access_method],
            checksums=[checksum],
            created_time=self.creation_date.isoformat(),
            id=accession,
            self_uri=f"{drs_server_uri_base}{accession}",
            size=size,
        )


class DrsObjectResponseModel(BaseModel):
    """A DRS compliant representation for the DrsObjectWithAccess model"""

    access_methods: list[AccessMethod]
    checksums: list[Checksum]
    created_time: str
    id: str  # this is the accession number provided in the request
    self_uri: str
    size: int

    @field_validator("self_uri")
    @classmethod
    def check_self_uri(cls, value: str):
        """Checks if the self_uri is a valid DRS URI."""
        if not re.match(r"^drs://.+/.+", value):
            raise ValueError(f"The self_uri '{value}' is no valid DRS URI.")

        return value


class FileInternallyRegistered(BaseModel):
    """An event schema communicating that a file has been copied into permanent storage.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """

    file_id: UUID4 = Field(..., description="Unique identifier for the file upload")
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


class NonStagedFileRequested(BaseModel):
    """
    This event type is triggered when a user requests to download a file that is not
    yet present in the download bucket and needs to be staged.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """

    file_id: UUID4 = Field(..., description="Unique identifier for the file upload")
    storage_alias: str = Field(
        default=..., description="The storage alias of the Data Hub housing the file"
    )
    target_bucket_id: str = Field(
        ...,
        description="The ID of the S3 bucket to which the object should be copied.",
    )
    target_object_id: UUID4 = Field(
        ..., description="The ID to use for the file in the download bucket."
    )
    decrypted_sha256: str = Field(
        ...,
        description="The SHA-256 checksum of the entire decrypted file content.",
    )
    model_config = ConfigDict(title="non_staged_file_requested")


class FileDeletionRequested(BaseModel):
    """
    This event is emitted when a request to delete a certain file from the file
    backend has been made.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """

    file_id: UUID4 = Field(..., description="Unique identifier for the file")


class FileDeletionSuccess(FileDeletionRequested):
    """
    This event is emitted when a service has deleted a file from its database as well
    as the S3 buckets it controls.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """


class FileRegisteredForDownload(BaseModel):
    """
    This event is triggered when a newly uploaded file becomes available for
    download via a GA4GH DRS-compatible API.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """

    file_id: UUID4 = Field(..., description="Unique identifier for the file")
    decrypted_sha256: str = Field(
        ...,
        description="The SHA-256 checksum of the entire decrypted file content.",
    )
    archive_date: UTCDatetime = Field(
        ...,
        description="The date and time when this file was archived.",
    )


class FileDownloadServed(NonStagedFileRequested):
    """
    This event type is triggered when a the content of a file was served
    for download. This event might be useful for auditing.

    This local definition will be replaced by the `ghga-event-schemas` definition
    once implemented there.
    """

    context: str = Field(
        ...,
        description=(
            "The context in which the download was served (e.g. the ID of the data"
            + " access request)."
        ),
    )
    model_config = ConfigDict(title="file_download_served")
