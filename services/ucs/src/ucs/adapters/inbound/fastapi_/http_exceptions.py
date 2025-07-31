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

"""A collextion of http exceptions."""

from ghga_service_commons.httpyexpect.server import HttpCustomExceptionBase
from pydantic import BaseModel

from ucs.core import models


class HttpNoFileAccessError(HttpCustomExceptionBase):
    """Thrown when the client has not sufficient privileges to access the specified
    file.
    """

    exception_id = "noFileAccess"

    class DataModel(BaseModel):
        """Model for exception data"""

        file_id: str

    def __init__(self, *, file_id: str, status_code: int = 403):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(
                "The user is not registered as a Data Submitter for the file with"
                + f" id {file_id}."
            ),
            data={"file_id": file_id},
        )


class HttpFileNotFoundError(HttpCustomExceptionBase):
    """Thrown when a file with given ID could not be found."""

    exception_id = "fileNotRegistered"

    class DataModel(BaseModel):
        """Model for exception data"""

        file_id: str

    def __init__(self, *, file_id: str, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(
                f"The file with ID {file_id} has not (yet) been registered for upload."
            ),
            data={"file_id": file_id},
        )


class HttpUploadNotFoundError(HttpCustomExceptionBase):
    """Thrown when an upload with given ID could not be found."""

    exception_id = "noSuchUpload"

    class DataModel(BaseModel):
        """Model for exception data"""

        upload_id: str

    def __init__(self, *, upload_id: str, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(f"The upload with ID {upload_id} does not exist."),
            data={"upload_id": upload_id},
        )


class HttpExistingActiveUploadError(HttpCustomExceptionBase):
    """Thrown when trying to create a new upload while there is another upload active."""

    exception_id = "existingActiveUpload"

    class DataModel(BaseModel):
        """Model for exception data"""

        file_id: str
        active_upload: models.UploadAttempt

    def __init__(
        self,
        *,
        file_id: str,
        active_upload: models.UploadAttempt,
        status_code: int = 400,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(
                f"An upload attempt with status {active_upload.status.value} is already"
                + "present for the file with ID {file_id}. Cannot create a new one."
            ),
            data={
                "file_id": file_id,
                "active_upload": active_upload.model_dump(mode="json"),
            },
        )


class HttpUploadNotPendingError(HttpCustomExceptionBase):
    """Thrown when updating an upload that cannot be uploaded anymore."""

    exception_id = "uploadNotPending"

    class DataModel(BaseModel):
        """Model for exception data"""

        upload_id: str
        current_upload_status: models.UploadStatus

    def __init__(
        self,
        *,
        upload_id: str,
        current_status: models.UploadStatus,
        status_code: int = 400,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(
                f"The upload with ID {upload_id} has the status {current_status}"
                + " and cannot be updated anymore."
            ),
            data={
                "upload_id": upload_id,
                "current_upload_status": current_status.value,
            },
        )


class HttpUploadStatusChangeError(HttpCustomExceptionBase):
    """Thrown when a problem occurred when trying to change the upload status."""

    exception_id = "uploadStatusChange"

    class DataModel(BaseModel):
        """Model for exception data"""

        upload_id: str
        target_status: models.UploadStatus

    def __init__(
        self,
        *,
        upload_id: str,
        target_status: models.UploadStatus,
        reason: str,
        status_code: int = 400,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(
                f"Failed to change the status of upload with id {upload_id} to"
                + f" '{target_status}': {reason}"
            ),
            data={"upload_id": upload_id, "target_status": target_status},
        )


class HttpUnknownStorageAliasError(HttpCustomExceptionBase):
    """Thrown when an upload to a storage node that does not exist was requested."""

    exception_id = "noSuchStorage"

    def __init__(self, *, storage_alias: str, status_code: int = 400):
        """Construct message and initialize exception"""
        super().__init__(
            status_code=status_code,
            description=(f"Storage node for alias {storage_alias} does not exist."),
            data={"storage_alias": storage_alias},
        )


class HttpFileNotFoundUploadError(HttpFileNotFoundError):
    """Needed to avoid key error in FastAPIs openapi generation."""
