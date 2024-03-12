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

Please note, these pydantic-based schemas are the source of truth for all other
schema representations such as json-schema.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from ghga_event_schemas.validation import validated_upload_date


class MetadataDatasetStage(str, Enum):
    """The current stage that a metadata dataset is in."""

    DOWNLOAD = "download"
    UPLOAD = "upload"


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
    model_config = ConfigDict(title="metadata_dataset_file", extra="allow")


class MetadataDatasetID(BaseModel):
    """Simplified model to pass dataset ID to claims repository for deletion"""

    accession: str = Field(..., description="The dataset accession.")


class SearchableResourceInfo(BaseModel):
    """Model containing only identifying information about an artifact's resource"""

    accession: str = Field(..., description="The resource accession.")
    class_name: str = Field(
        ...,
        description="The name of the class this artifact resource corresponds to.",
    )


class SearchableResource(SearchableResourceInfo):
    """Model containing resource content in addition to the accession and class name"""

    content: dict[str, Any] = Field(
        ..., description="The metadata content of this artifact resource."
    )


class MetadataDatasetOverview(MetadataDatasetID):
    """
    Overview of files contained in a dataset.
    Only fields relevant to the WPS are included for now. May be extended.
    """

    title: str = Field(..., description="The title of the dataset.")
    stage: MetadataDatasetStage = Field(
        ..., description="The current stage of this dataset."
    )
    description: Optional[str] = Field(
        ..., description="The description of the dataset."
    )
    files: list[MetadataDatasetFile] = Field(
        ..., description="Files contained in the dataset."
    )
    model_config = ConfigDict(title="metadata_dataset_overview", extra="allow")


class UploadDateModel(BaseModel):
    """
    Custom base model for common datetime validation.
    Models containing stringified upload_date datetimes should be derived from this.
    """

    upload_date: str = Field(
        ...,
        description="The date and time when this file was uploaded."
        + "String format should follow ISO 8601 as produced by datetime.utcnow().isoformat()",
    )

    @field_validator("upload_date")
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
        examples=["treatment_R1.fastq.gz"],
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
    model_config = ConfigDict(title="metadata_submission_upserted")


class FileUploadReceived(UploadDateModel):
    """This event is triggered when a new file upload is received."""

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
    s3_endpoint_alias: str = Field(
        ...,
        description="Alias for the object storage location where the given object is stored."
        + "This can be uniquely mapped to an endpoint configuration in the service.",
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
    model_config = ConfigDict(title="file_upload_received")


class FileUploadValidationSuccess(UploadDateModel):
    """This event is triggered when an uploaded file is successfully validated."""

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )
    object_id: str = Field(
        ..., description="The ID of the file in the specific S3 bucket."
    )
    bucket_id: str = Field(
        ..., description="The ID/name of the S3 bucket used to store the file."
    )
    s3_endpoint_alias: str = Field(
        ...,
        description="Alias for the object storage location where the given object is stored."
        + "This can be uniquely mapped to an endpoint configuration in the service.",
    )
    decrypted_size: int = Field(
        ...,
        description="The size of the entire decrypted file content in bytes.",
    )
    decryption_secret_id: str = Field(
        ...,
        description=(
            "The ID of the symmetric file encryption/decryption secret."
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
    model_config = ConfigDict(title="file_upload_validation_success")


class FileUploadValidationFailure(UploadDateModel):
    """This event is triggered when an uploaded file failed to validate."""

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
    s3_endpoint_alias: str = Field(
        ...,
        description="Alias for the object storage location where the given object is stored."
        + "This can be uniquely mapped to an endpoint configuration in the service.",
    )
    reason: str = Field(
        ...,
        description="The reason why the validation failed.",
    )
    model_config = ConfigDict(title="file_upload_validation_failure")


class FileInternallyRegistered(FileUploadValidationSuccess):
    """This event is triggered when an newly uploaded file is internally registered."""

    model_config = ConfigDict(title="file_internally_registered")


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
    model_config = ConfigDict(title="file_registered_for_download")


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
    s3_endpoint_alias: str = Field(
        ...,
        description="Alias for the object storage location where the given object is stored."
        + "This can be uniquely mapped to an endpoint configuration in the service.",
    )
    decrypted_sha256: str = Field(
        ...,
        description="The SHA-256 checksum of the entire decrypted file content.",
    )
    model_config = ConfigDict(title="non_staged_file_requested")


class FileStagedForDownload(NonStagedFileRequested):
    """This event type is triggered when a file is staged to the outbox storage."""

    model_config = ConfigDict(title="file_staged_for_download")


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
    model_config = ConfigDict(title="file_download_served")


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
    model_config = ConfigDict(title="notification")


class FileDeletionRequested(BaseModel):
    """
    This event is emitted when a request to delete a certain file from the file
    backend has been made.
    """

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )
    model_config = ConfigDict(title="file_deletion_requested")


class FileDeletionSuccess(FileDeletionRequested):
    """
    This event is emitted when a service has deleted a file from its database as well
    as the S3 buckets it controls.
    """

    model_config = ConfigDict(title="file_deletion_success")


class UserID(BaseModel):
    """Generic event payload to relay a user ID."""

    user_id: str


class AccessRequestDetails(UserID):
    """Event used to convey the user ID and dataset ID of an access request."""

    dataset_id: str


# Lists event schemas (values) by event types (key):
schema_registry: dict[str, type[BaseModel]] = {
    "metadata_dataset_deleted": MetadataDatasetID,
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
    "searchable_resource_deleted": SearchableResourceInfo,
    "searchable_resource_upserted": SearchableResource,
    "user_id": UserID,
    "access_request_details": AccessRequestDetails,
}
