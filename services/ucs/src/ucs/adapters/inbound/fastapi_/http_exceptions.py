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
from pydantic import UUID4, BaseModel


class HttpUnknownStorageAliasError(HttpCustomExceptionBase):
    """Thrown when an upload to a storage node that does not exist was requested."""

    exception_id = "noSuchStorage"

    def __init__(self, *, status_code: int = 400):
        """Construct message and initialize exception"""
        super().__init__(
            status_code=status_code,
            description=("There was a problem identifying the storage alias."),
            data={},
        )


class HttpBoxNotFoundError(HttpCustomExceptionBase):
    """Thrown when a FileUploadBox with given ID could not be found."""

    exception_id = "boxNotFound"

    class DataModel(BaseModel):
        """Model for exception data"""

        box_id: UUID4

    def __init__(self, *, box_id: UUID4, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(f"FileUploadBox with ID {box_id} not found."),
            data={"box_id": str(box_id)},
        )


class HttpLockedBoxError(HttpCustomExceptionBase):
    """Thrown when trying to perform an action on a locked FileUploadBox."""

    exception_id = "lockedBox"

    class DataModel(BaseModel):
        """Model for exception data"""

        box_id: UUID4

    def __init__(self, *, box_id: UUID4, status_code: int = 409):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(
                f"Can't perform this action because the box with ID {box_id} is locked."
            ),
            data={"box_id": str(box_id)},
        )


class HttpFileUploadAlreadyExistsError(HttpCustomExceptionBase):
    """Thrown when trying to create a FileUpload that already exists for a given alias."""

    exception_id = "fileUploadAlreadyExists"

    class DataModel(BaseModel):
        """Model for exception data"""

        alias: str

    def __init__(self, *, alias: str, status_code: int = 409):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(
                f"Failed to create a FileUpload for the alias {alias} because"
                + " another one with the same alias already exists."
            ),
            data={"alias": alias},
        )


class HttpOrphanedMultipartUploadError(HttpCustomExceptionBase):
    """Thrown when a multipart upload is already in progress for a file."""

    exception_id = "orphanedMultipartUpload"

    class DataModel(BaseModel):
        """Model for exception data"""

        file_alias: str

    def __init__(self, *, file_alias: str, status_code: int = 409):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(
                f"A multipart upload is already in progress for file {file_alias}, but"
                + " cannot be aborted due to a system error. Please request file"
                + " deletion and then attempt the upload again."
            ),
            data={"file_alias": file_alias},
        )


class HttpS3UploadDetailsNotFoundError(HttpCustomExceptionBase):
    """Thrown when S3 upload details for a file cannot be found."""

    exception_id = "s3UploadDetailsNotFound"

    class DataModel(BaseModel):
        """Model for exception data"""

        file_id: UUID4

    def __init__(self, *, file_id: UUID4, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(f"S3 upload details for file ID {file_id} were not found."),
            data={"file_id": str(file_id)},
        )


class HttpS3UploadNotFoundError(HttpCustomExceptionBase):
    """Thrown when an S3 multipart upload cannot be found."""

    exception_id = "s3UploadNotFound"

    def __init__(self, *, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="S3 multipart upload not found.",
            data={},
        )


class HttpFileUploadNotFoundError(HttpCustomExceptionBase):
    """Thrown when a FileUpload with given ID could not be found."""

    exception_id = "fileUploadNotFound"

    class DataModel(BaseModel):
        """Model for exception data"""

        file_id: UUID4

    def __init__(self, *, file_id: UUID4, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(f"FileUpload with ID {file_id} not found."),
            data={"file_id": str(file_id)},
        )


class HttpUploadCompletionError(HttpCustomExceptionBase):
    """Thrown when there's an error completing the multipart upload."""

    exception_id = "uploadCompletionError"

    class DataModel(BaseModel):
        """Model for exception data"""

        box_id: UUID4
        file_id: UUID4

    def __init__(self, *, box_id: UUID4, file_id: UUID4, status_code: int = 500):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="An error occurred while completing the file upload. Delete the"
            + " file from the file upload box and retry.",
            data={"box_id": str(box_id), "file_id": str(file_id)},
        )


class HttpUploadAbortError(HttpCustomExceptionBase):
    """Thrown when there's an error aborting the multipart upload."""

    exception_id = "uploadAbortError"

    def __init__(self, *, status_code: int = 500):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="An error occurred while canceling the file upload.",
            data={},
        )


class HttpNotAuthorizedError(HttpCustomExceptionBase):
    """Thrown when the user is not authorized to perform the requested action."""

    exception_id = "notAuthorized"

    def __init__(self, *, status_code: int = 403):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="Not authorized",
            data={},
        )


class HttpInternalError(HttpCustomExceptionBase):
    """Thrown for otherwise unhandled exceptions"""

    exception_id = "internalError"

    def __init__(self, *, status_code: int = 500):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="An internal server error has occurred.",
            data={},
        )
