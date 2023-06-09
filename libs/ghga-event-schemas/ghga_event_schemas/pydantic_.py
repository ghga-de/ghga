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

"""Contains pydantic BaseModel-based versions of the schemas.

Please note, these pydantic-based schemas are the source of thruth for all other
schema representations such as json-schema.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator

from ghga_event_schemas.validation import validated_upload_date


class MetadataDatasetFile(BaseModel):
    """
    A file as that is part of a Dataset.
    Only fields relevant to the WPS are included for now. May be extended.
    """

    accession: str = Field(..., description="The file accession.")
    description: Optional[str] = Field(..., description="The description of the file.")
    file_extension: str = Field(
        ..., description="The file extension with a leading dot."
    )

    class Config:
        """Model config."""

        title = "metadata_dataset_file"
        extra = "allow"


class MetadataDatasetOverview(BaseModel):
    """
    Overview of files contained in a dataset.
    Only fields relevant to the WPS are included for now. May be extended.
    """

    accession: str = Field(..., description="The dataset accession.")
    title: str = Field(..., description="The title of the dataset.")
    description: Optional[str] = Field(
        ..., description="The description of the dataset."
    )
    files: list[MetadataDatasetFile] = Field(
        ..., description="Files contained in the dataset."
    )

    class Config:
        """Model config."""

        title = "metadata_dataset_overview"
        extra = "allow"


class UploadDateModel(BaseModel):
    """
    Custom base model for common datetime validation.
    Models containing stringified upload_date datetimes should be dervied from this.
    """

    upload_date: str = Field(
        ...,
        description="The date and time when this file was uploaded."
        + "String format should follow ISO 8601 as produced by datetime.utcnow().isoformat()",
    )

    @validator("upload_date")
    @classmethod
    def check_datetime_format(cls, upload_date):
        """Validate provided upload date string can be interpreted as datetime"""
        return validated_upload_date(upload_date)


class MetadataSubmissionFiles(BaseModel):
    """
    Models files that are associated with or affected by a new or updated metadata
    submission.
    """

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )
    file_name: str = Field(
        ...,
        description="The name of the file as it was submitted.",
        example="treatment_R1.fastq.gz",
    )
    decrypted_size: int = Field(
        ...,
        description="The size of the entire decrypted file content in bytes.",
    )
    decrypted_sha256: str = Field(
        ..., description="The SHA-2 checksum of the entire decrypted file content."
    )


class MetadataSubmissionUpserted(BaseModel):
    """
    This event when a new metadata submission is created or an existing one is
    updated.
    """

    associated_files: list[MetadataSubmissionFiles]

    class Config:
        """Additional Model Config."""

        title = "metadata_submission_upserted"


class FileUploadReceived(UploadDateModel):
    """
    This event is triggered when a new file upload is received.
    """

    file_id: str = Field(
        ...,
        description="The public ID of the file as present in the metadata catalog.",
    )
    object_id: str = Field(
        ..., description="The ID of the file in the specific S3 bucket."
    )
    bucket_id: str = Field(
        ..., description="The ID/name of the S3 bucket used to store the file."
    )
    submitter_public_key: str = Field(
        ...,
        description="The public key of the submitter.",
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


class FileUploadValidationSuccess(UploadDateModel):
    """
    This event is triggered when an uploaded file is successfully validated.
    """

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )
    object_id: str = Field(
        ..., description="The ID of the file in the specific S3 bucket."
    )
    bucket_id: str = Field(
        ..., description="The ID/name of the S3 bucket used to store the file."
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

    class Config:
        """Additional Model Config."""

        title = "file_upload_validation_success"


class FileUploadValidationFailure(UploadDateModel):
    """
    This event is triggered when an uploaded file failed to validate.
    """

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )
    object_id: str = Field(
        ..., description="The ID of the file in the specific S3 bucket."
    )
    bucket_id: str = Field(
        ...,
        description="The ID/name of the S3 bucket used to store the file.",
    )
    reason: str = Field(
        ...,
        description="The reason why the validation failed.",
    )

    class Config:
        """Additional Model Config."""

        title = "file_upload_validation_failure"


class FileInternallyRegistered(FileUploadValidationSuccess):
    """
    This event is triggered when an newly uploaded file is internally registered.
    """

    # currently identical to the FileUploadValidationSuccess event model

    class Config:
        """Additional Model Config."""

        title = "file_internally_registered"


class FileRegisteredForDownload(UploadDateModel):
    """
    This event is triggered when a newly uploaded file becomes available for
    download via a GA4GH DRS-compatible API.
    """

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
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
    """
    This event type is triggered when a user requests to download a file that is not
    yet present in the outbox and needs to be staged.
    """

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )
    target_object_id: str = Field(
        ..., description="The ID of the file in the specific S3 bucket."
    )
    target_bucket_id: str = Field(
        ...,
        description="The ID/name of the S3 bucket in which the object was expected.",
    )
    decrypted_sha256: str = Field(
        ...,
        description="The SHA-256 checksum of the entire decrypted file content.",
    )

    class Config:
        """Additional Model Config."""

        title = "non_staged_file_requested"


class FileStagedForDownload(NonStagedFileRequested):
    """
    This event type is triggered when a file is staged to the outbox storage.
    """

    # currently identical to the NonStagedFileRequested event model.

    class Config:
        """Additional Model Config."""

        title = "file_staged_for_download"


class FileDownloadServed(NonStagedFileRequested):
    """
    This event type is triggered when a the content of a file was served
    for download. This event might be useful for auditing.
    """

    context: str = Field(
        ...,
        description=(
            "The context in which the download was served (e.g. the ID of the data"
            + " access request)."
        ),
    )

    class Config:
        """Additional Model Config."""

        title = "file_download_served"


class Notification(BaseModel):
    """
    This event is emitted by services that desire to send a notification.
    It is picked up by the notification service.
    """

    recipient_email: EmailStr = Field(
        ..., description="The primary recipient of the email"
    )
    email_cc: list[EmailStr] = Field(
        default=[], description="The list of recipients cc'd on the email"
    )
    email_bcc: list[EmailStr] = Field(
        default=[], description="The list of recipients bcc'd on the email"
    )
    subject: str = Field(..., description="The subject line for the notification")
    recipient_name: str = Field(
        ...,
        description="The full name of the recipient to be used in the greeting section",
    )
    plaintext_body: str = Field(
        ..., description="The basic text for the notification body"
    )

    class Config:
        """Additional Model Config."""

        title = "notification"


class FileDeletionRequested(BaseModel):
    """
    This event is emitted when a request to delete a certain file from the file
    backend has been made.
    """

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )

    class Config:
        """Additional Model Config."""

        title = "file_deletion_requested"


class FileDeletionSuccess(FileDeletionRequested):
    """
    This event is emitted when a service has deleted a file from its database as well
    as the S3 buckets it controlls.
    """

    # currently identical to the FileDeletionRequested event model.

    class Config:
        """Additional Model Config."""

        title = "file_deletion_success"


# Lists event schemas (values) by event types (key):
schema_registry: dict[str, type[BaseModel]] = {
    "metadata_dataset_overview": MetadataDatasetOverview,
    "metadata_submission_upserted": MetadataSubmissionUpserted,
    "file_upload_received": FileUploadReceived,
    "file_upload_validation_success": FileUploadValidationSuccess,
    "file_upload_validation_failure": FileUploadValidationFailure,
    "file_internally_registered": FileInternallyRegistered,
    "file_registered_for_download": FileRegisteredForDownload,
    "non_staged_file_requested": NonStagedFileRequested,
    "file_staged_for_download": FileStagedForDownload,
    "file_download_served": FileDownloadServed,
    "notification": Notification,
}
