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

"""A collextion of http exceptions."""

from ghga_event_schemas.pydantic_ import UploadBoxState
from ghga_service_commons.httpyexpect.server import HttpCustomExceptionBase
from pydantic import UUID4, BaseModel


class HttpUnknownStorageAliasError(HttpCustomExceptionBase):
    """Thrown when an upload to a storage node that does not exist was requested."""

    exception_id = "noSuchStorage"

    def __init__(self, *, status_code: int = 400):
        """Construct message and initialize exception"""
        super().__init__(
            status_code=status_code,
            description="",
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
            description="",
            data={"box_id": str(box_id)},
        )


class HttpBoxStateError(HttpCustomExceptionBase):
    """Thrown when the user requests an action FileUploadBox prevented by the box's state."""

    exception_id = "boxStateError"

    class DataModel(BaseModel):
        """Model for exception data"""

        box_id: UUID4
        box_state: UploadBoxState

    def __init__(
        self, *, box_id: UUID4, box_state: UploadBoxState, status_code: int = 409
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="",
            data={"box_id": str(box_id), "box_state": box_state},
        )


class HttpBoxVersionError(HttpCustomExceptionBase):
    """Thrown when a request referenced an outdated resource state."""

    exception_id = "boxVersionOutdated"

    class DataModel(BaseModel):
        """Model for exception data"""

        box_id: UUID4

    def __init__(self, *, box_id: UUID4, status_code: int = 409):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="",
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
            description="",
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
            description="",
            data={"file_alias": file_alias},
        )


class HttpS3UploadNotFoundError(HttpCustomExceptionBase):
    """Thrown when an S3 multipart upload cannot be found."""

    exception_id = "s3UploadNotFound"

    def __init__(self, *, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="",
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
            description="",
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
            description="",
            data={"box_id": str(box_id), "file_id": str(file_id)},
        )


class HttpUploadAbortError(HttpCustomExceptionBase):
    """Thrown when there's an error aborting the multipart upload."""

    exception_id = "uploadAbortError"

    def __init__(self, *, status_code: int = 500):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="",
            data={},
        )


class HttpChecksumMismatchError(HttpCustomExceptionBase):
    """Thrown when the user-supplied encrypted checksum doesn't match S3."""

    exception_id = "checksumMismatch"

    class DataModel(BaseModel):
        """Model for exception data"""

        file_id: UUID4

    def __init__(self, *, file_id: UUID4, status_code: int = 400):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="",
            data={"file_id": str(file_id)},
        )


class HttpUploadSizeMismatchError(HttpCustomExceptionBase):
    """Thrown when the actual uploaded object size doesn't match the declared encrypted_size."""

    exception_id = "uploadSizeMismatch"

    class DataModel(BaseModel):
        """Model for exception data"""

        file_id: UUID4

    def __init__(self, *, file_id: UUID4, status_code: int = 400):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="",
            data={"file_id": str(file_id)},
        )


class HttpMaxSizeTooLowError(HttpCustomExceptionBase):
    """Thrown when the requested max_size is less than the box's current committed size."""

    exception_id = "boxMaxSizeTooLow"

    class DataModel(BaseModel):
        """Model for exception data"""

        box_id: UUID4
        max_size: int
        current_size: int

    def __init__(
        self,
        *,
        box_id: UUID4,
        max_size: int,
        current_size: int,
        status_code: int = 409,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="",
            data={
                "box_id": str(box_id),
                "max_size": max_size,
                "current_size": current_size,
            },
        )


class HttpBoxMaxSizeExceededError(HttpCustomExceptionBase):
    """Thrown when adding a file would exceed the box's total size limit."""

    exception_id = "boxMaxSizeExceeded"

    class DataModel(BaseModel):
        """Model for exception data"""

        box_id: UUID4
        max_size: int
        current_size: int
        file_alias: str

    def __init__(
        self,
        *,
        box_id: UUID4,
        max_size: int,
        current_size: int,
        file_alias: str,
        status_code: int = 507,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="",
            data={
                "box_id": str(box_id),
                "max_size": max_size,
                "current_size": current_size,
                "file_alias": file_alias,
            },
        )


class HttpTooManyOpenUploadsError(HttpCustomExceptionBase):
    """Thrown when a box already has the maximum number of concurrent in-progress uploads."""

    exception_id = "tooManyOpenUploads"

    class DataModel(BaseModel):
        """Model for exception data"""

        box_id: UUID4
        max_concurrent: int

    def __init__(
        self,
        *,
        box_id: UUID4,
        max_concurrent: int,
        status_code: int = 429,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="",
            data={"box_id": str(box_id), "max_concurrent": max_concurrent},
        )


class HttpPartSizeError(HttpCustomExceptionBase):
    """Thrown when the specified part size is invalid."""

    exception_id = "invalidPartSize"

    class DataModel(BaseModel):
        """Model for exception data"""

        file_alias: str
        part_size: int

    def __init__(self, *, file_alias: str, part_size: int, status_code: int = 400):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="",
            data={"file_alias": file_alias, "part_size": part_size},
        )


class HttpIncompleteUploadsError(HttpCustomExceptionBase):
    """Thrown when locking or archiving a box that still has in-progress uploads."""

    exception_id = "incompleteUploads"

    class DataModel(BaseModel):
        """Model for exception data"""

        box_id: UUID4
        file_ids: list[tuple[UUID4, str]]

    def __init__(
        self,
        *,
        box_id: UUID4,
        file_ids: list[tuple[UUID4, str]],
        status_code: int = 409,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="",
            data={
                "box_id": str(box_id),
                "file_ids": [[str(fid), alias] for fid, alias in file_ids],
            },
        )


class HttpFileUploadStateError(HttpCustomExceptionBase):
    """Thrown when an action is incompatible with the FileUpload's current state."""

    exception_id = "fileUploadStateError"

    class DataModel(BaseModel):
        """Model for exception data"""

        file_id: UUID4

    def __init__(self, *, file_id: UUID4, status_code: int = 409):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="",
            data={"file_id": str(file_id)},
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


class HttpPaginationError(HttpCustomExceptionBase):
    """Thrown when the skip or limit pagination parameters are invalid."""

    exception_id = "paginationError"

    def __init__(self, *, status_code: int = 422):
        """Construct message and initialize exception."""
        super().__init__(
            status_code=status_code,
            description="",
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
