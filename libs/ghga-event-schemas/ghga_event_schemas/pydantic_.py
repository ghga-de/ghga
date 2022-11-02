# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""Contains pydantic BaseModel-based versions of the schemas.

Please note, these pydantic-based schemas are the source of thruth for all other
schema representations such as json-schema.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class MetadataSubmissionFiles(BaseModel):
    """Models files that are associated with or affected by a new or updated metadata
    submission."""

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )
    decrypted_size: int = Field(
        ...,
        description="The size of the entire decrypted file content in bytes.",
    )
    decrypted_sha256: str = Field(
        ..., description="The SHA-2 checksum of the entire decrypted file content."
    )


class MetadataSubmissionUpserted(BaseModel):
    """This event when a new metadata submission is created or an existing one is
    updated."""

    associated_files: list[MetadataSubmissionFiles]

    class Config:
        """Additional Model Config."""

        title = "metadata_submission_upserted"


class FileUploadReceived(BaseModel):
    """This event is triggered when an new file upload was received."""

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )
    upload_date: datetime = Field(
        ...,
        description="The date and time when this file was uploaded.",
    )
    decrypted_size: int = Field(
        ...,
        description="The size of the entire decrypted file content in bytes.",
    )
    expected_decrypted_sha256: str = Field(
        ...,
        description=(
            "The expected SHA-256 checksum of the entire decrypted file content."
            + " To be validated."
        ),
    )

    class Config:
        """Additional Model Config."""

        title = "file_upload_received"


class FileUploadValidationSuccess(BaseModel):
    """This event is triggered when an uploaded file was successfully validated."""

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )
    upload_date: datetime = Field(
        ...,
        description="The date and time when this file was uploaded.",
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
            + " crypt4GH) as used for the encryption_parts_md5 and the"
            + " encryption_parts_sha256 in bytes. The same part size is recommended for"
            + " moving that content."
        ),
    )
    encrypted_parts_md5: list[str] = Field(
        ...,
        description=(
            "MD5 checksums of file parts of the encrypted content (excluding the"
            + " crypt4gh envelope."
        ),
    )
    encrypted_parts_sha256: list[str] = Field(
        ...,
        description=(
            "SHA-256 checksums of file parts of the encrypted content (excluding the"
            + " crypt4gh envelope."
        ),
    )
    decrypted_sha256: str = Field(
        ...,
        description="The SHA-256 checksum of the entire decrypted file content.",
    )

    class Config:
        """Additional Model Config."""

        title = "file_upload_validation_success"


class FileUploadValidationFailure(BaseModel):
    """This event is triggered when an uploaded file failed to validate."""

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )
    upload_date: datetime = Field(
        ...,
        description="The date and time when this file was uploaded.",
    )
    reason: str = Field(
        ...,
        description="The reason why the validation failed.",
    )

    class Config:
        """Additional Model Config."""

        title = "file_upload_validation_failure"


class FileInternallyRegistered(FileUploadValidationSuccess):
    """This event is triggered when an newly uploaded file is internally registered."""

    # currently identical to the FileUploadValidationSuccess event model.

    class Config:
        """Additional Model Config."""

        title = "file_internally_registered"


class FileRegisteredForDownload(BaseModel):
    """This event is triggered when a newly uploaded file becomes available for
    download via a GA4GH DRS-compatible API."""

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )
    upload_date: datetime = Field(
        ...,
        description="The date and time when this file was uploaded.",
    )
    decrypted_sha256: str = Field(
        ...,
        description="The SHA-256 checksum of the entire decrypted file content.",
    )
    drs_uri: str = Field(
        ...,
        description="A URI for accessing the file according to the GA4GH DRS standard.",
    )

    class Config:
        """Additional Model Config."""

        title = "file_registered_for_download"


class NonStagedFileRequested(BaseModel):
    """This event type is triggered when a user requested to download a file that is not
    yet present in the outbox and need to be staged."""

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )
    decrypted_sha256: str = Field(
        ...,
        description="The SHA-256 checksum of the entire decrypted file content.",
    )

    class Config:
        """Additional Model Config."""

        title = "non_staged_file_requested"


class FileStagedForDownload(NonStagedFileRequested):
    """This event type is triggered when a file is staged to the outbox storage."""

    # currently identical to the NonStagedFileRequested event model.

    class Config:
        """Additional Model Config."""

        title = "file_staged_for_download"


# Lists event schemas (values) by event types (key):
schema_registry: dict[str, type[BaseModel]] = {
    "metadata_submission_upserted": MetadataSubmissionUpserted,
    "file_upload_received": FileUploadReceived,
    "file_upload_validation_success": FileUploadValidationSuccess,
    "file_upload_validation_failure": FileUploadValidationFailure,
    "file_internally_registered": FileInternallyRegistered,
    "file_registered_for_download": FileRegisteredForDownload,
    "non_staged_file_requested": NonStagedFileRequested,
    "file_staged_for_download": FileStagedForDownload,
}
