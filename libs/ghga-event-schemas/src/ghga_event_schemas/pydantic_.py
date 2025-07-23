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

"""Contains pydantic BaseModel-based versions of the schemas.

Please note, these pydantic-based schemas are the source of truth for all other
schema representations such as json-schema.
"""

from enum import StrEnum
from typing import Any

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, BaseModel, ConfigDict, EmailStr, Field


class MetadataDatasetStage(StrEnum):
    """The current stage that a metadata dataset is in."""

    DOWNLOAD = "download"
    UPLOAD = "upload"


class MetadataDatasetFile(BaseModel):
    """
    A file as that is part of a Dataset.
    Only fields relevant to the WPS are included for now. May be extended.
    """

    accession: str = Field(..., description="The file accession.")
    description: str | None = Field(..., description="The description of the file.")
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


class ArtifactTag(BaseModel):
    """A model representing a tag for an artifact (artifact name and study accession)."""

    study_accession: str = Field(
        ..., description="The ID of the study this artifact pertains to."
    )
    artifact_name: str = Field(
        ..., description="The name of the artifact, e.g. 'added_accessions'."
    )


class Artifact(ArtifactTag):
    """A model representing an artifact."""

    content: dict[str, Any] = Field(
        ..., description="The metadata content of the artifact."
    )


class MetadataDatasetOverview(MetadataDatasetID):
    """
    Overview of files contained in a dataset.
    Only fields relevant to the WPS are included for now. May be extended.
    """

    title: str = Field(..., description="The title of the dataset")
    stage: MetadataDatasetStage = Field(
        ..., description="The current stage of this dataset"
    )
    description: str | None = Field(..., description="The description of the dataset")
    dac_alias: str = Field(..., description="The alias of the Data Access Committee")
    dac_email: EmailStr = Field(
        ..., description="The email address of the Data Access Committee"
    )
    files: list[MetadataDatasetFile] = Field(
        ..., description="Files contained in the dataset"
    )
    model_config = ConfigDict(title="metadata_dataset_overview", extra="allow")


class UploadDateModel(BaseModel):
    """
    Custom base model for common datetime validation.
    Models containing upload_date datetimes should be derived from this.
    """

    upload_date: UTCDatetime = Field(
        ...,
        description="The date and time when this file was uploaded.",
    )


class FileIdModel(BaseModel):
    """Base model for events that contain a file ID."""

    file_id: str = Field(
        ..., description="The public ID of the file as present in the metadata catalog."
    )


class MetadataSubmissionFiles(FileIdModel):
    """
    Models files that are associated with or affected by a new or updated metadata
    submission.
    """

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


class FileUploadReceived(UploadDateModel, FileIdModel):
    """This event is triggered when a new file upload is received."""

    object_id: UUID4 = Field(
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


class FileUploadValidationSuccess(UploadDateModel, FileIdModel):
    """This event is triggered when an uploaded file is successfully validated."""

    object_id: UUID4 = Field(
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


class FileUploadValidationFailure(UploadDateModel, FileIdModel):
    """This event is triggered when an uploaded file failed to validate."""

    object_id: UUID4 = Field(
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

    encrypted_size: int = Field(
        ...,
        description="The size of the encrypted file content in bytes without the Crypt4GH envelope.",
    )

    model_config = ConfigDict(title="file_internally_registered")


class FileRegisteredForDownload(UploadDateModel, FileIdModel):
    """
    This event is triggered when a newly uploaded file becomes available for
    download via a GA4GH DRS-compatible API.
    """

    decrypted_sha256: str = Field(
        ...,
        description="The SHA-256 checksum of the entire decrypted file content.",
    )
    drs_uri: str = Field(
        ...,
        description="A URI for accessing the file according to the GA4GH DRS standard.",
    )
    model_config = ConfigDict(title="file_registered_for_download")


class NonStagedFileRequested(FileIdModel):
    """
    This event type is triggered when a user requests to download a file that is not
    yet present in the outbox and needs to be staged.
    """

    target_object_id: UUID4 = Field(
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


class FileDeletionRequested(FileIdModel):
    """
    This event is emitted when a request to delete a certain file from the file
    backend has been made.
    """

    model_config = ConfigDict(title="file_deletion_requested")


class FileDeletionSuccess(FileDeletionRequested):
    """
    This event is emitted when a service has deleted a file from its database as well
    as the S3 buckets it controls.
    """

    model_config = ConfigDict(title="file_deletion_success")


class UserID(BaseModel):
    """Generic event payload to relay a user ID."""

    user_id: UUID4 = Field(..., description="The user ID")


class AcademicTitle(StrEnum):
    """Academic title"""

    DR = "Dr."
    PROF = "Prof."


class User(UserID):
    """Event used to publish user data changes via outbox pattern."""

    name: str = Field(
        default=...,
        description="Full name of the user",
        examples=["Rosalind Franklin"],
    )
    title: AcademicTitle | None = Field(
        default=None, title="Academic title", description="Academic title of the user"
    )
    email: EmailStr = Field(
        default=...,
        description="Preferred e-mail address of the user",
        examples=["user@home.org"],
    )


class AccessRequestStatus(StrEnum):
    """The status of an access request."""

    ALLOWED = "allowed"
    DENIED = "denied"
    PENDING = "pending"


class AccessRequestDetails(UserID):
    """Event used to convey the details an access request."""

    id: UUID4 = Field(..., description="The access request ID")
    dataset_id: str = Field(..., description="The dataset ID")
    dataset_title: str = Field(..., description="The dataset title")
    dataset_description: str | None = Field(
        default=None, description="A description of the dataset"
    )
    status: AccessRequestStatus = Field(
        default=...,
        description="The status of the access request",
    )
    request_text: str = Field(
        default=..., description="Text note submitted with the request"
    )
    dac_alias: str = Field(
        ...,
        description="The alias of the Data Access Committee responsible for the dataset",
    )
    dac_email: EmailStr = Field(
        ..., description="The email address of the Data Access Committee"
    )
    ticket_id: str | None = Field(
        default=None,
        description="The ID of the ticket associated with the access request",
    )
    internal_note: str | None = Field(
        default=None,
        description="A note about the access request only visible to Data Stewards",
    )
    note_to_requester: str | None = Field(
        default=None,
        description="A note about the access request that is visible to the requester",
    )
    access_starts: UTCDatetime = Field(
        ...,
        description="The beginning of the access request's validity period as a UTC datetime",
    )
    access_ends: UTCDatetime = Field(
        ...,
        description="The end of the access request's validity period as a UTC datetime",
    )


class IvaType(StrEnum):
    """The type of IVA"""

    PHONE = "Phone"
    FAX = "Fax"
    POSTAL_ADDRESS = "PostalAddress"
    IN_PERSON = "InPerson"


class IvaState(StrEnum):
    """The state of an IVA"""

    UNVERIFIED = "Unverified"
    CODE_REQUESTED = "CodeRequested"
    CODE_CREATED = "CodeCreated"
    CODE_TRANSMITTED = "CodeTransmitted"
    VERIFIED = "Verified"


class UserIvaState(UserID):
    """Notification event for state changes of a user's IVA(s)."""

    value: str | None = Field(
        default=..., description="The value of the IVA (None = all IVAs of the user)"
    )
    type: IvaType | None = Field(
        default=..., description="The type of the IVA (None = all IVAs of the user"
    )
    state: IvaState = Field(..., description="The new state of the IVA")

    model_config = ConfigDict(title="iva_state_change")


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
    "second_factor_recreated": UserID,
    "access_request_details": AccessRequestDetails,
    "iva_state_changed": UserIvaState,
}
