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

"""A collection of http exceptions."""

from ghga_service_commons.httpyexpect.server import HttpCustomExceptionBase
from pydantic import UUID4, BaseModel

__all__ = [
    "HttpAccessionMapError",
    "HttpArchivalPrereqsError",
    "HttpBoxMaxSizeTooLowError",
    "HttpBoxNotFoundError",
    "HttpBoxStateError",
    "HttpBoxTitleExistsError",
    "HttpBoxVersionError",
    "HttpGrantNotFoundError",
    "HttpIncompleteUploadsError",
    "HttpInternalError",
    "HttpNotAuthorizedError",
    "HttpStateChangeError",
]


class HttpAccessionMapError(HttpCustomExceptionBase):
    """Thrown when an accession map submission fails for any map-related reason.

    The `error_type` field in the response body identifies the specific failure.
    See `RDUBManagerPort.AccessionMapError` for the full set of values and which
    accompanying lists are populated for each.
    """

    exception_id = "accessionMapError"

    class DataModel(BaseModel):
        """Model for exception data"""

        error_type: str
        conflicting_accessions: list[str] = []
        affected_file_ids: list[str] = []

    def __init__(
        self,
        *,
        error_type: str,
        conflicting_accessions: list[str] | None = None,
        affected_file_ids: list[str] | None = None,
        status_code: int = 409,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="Accession map submission failed.",
            data={
                "error_type": error_type,
                "conflicting_accessions": conflicting_accessions or [],
                "affected_file_ids": affected_file_ids or [],
            },
        )


class HttpBoxTitleExistsError(HttpCustomExceptionBase):
    """Thrown when a FileUploadBox with the given title already exists."""

    exception_id = "boxTitleExists"

    class DataModel(BaseModel):
        """Model for exception data"""

        title: str

    def __init__(self, *, title: str, status_code: int = 409):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=f"A ResearchDataUploadBox with the title '{title}' already exists.",
            data={"title": title},
        )


class HttpArchivalPrereqsError(HttpCustomExceptionBase):
    """Thrown when archival prerequisites are not met (e.g. files missing accessions)."""

    exception_id = "archivalPrereqsNotMet"

    def __init__(self, *, status_code: int = 409):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="Archival prerequisites are not met.",
            data={},
        )


class HttpBoxMaxSizeTooLowError(HttpCustomExceptionBase):
    """Thrown when the requested max size is smaller than bytes already uploaded."""

    exception_id = "boxMaxSizeTooLow"

    def __init__(self, *, status_code: int = 409):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="The requested max size is lower than the bytes already uploaded.",
            data={},
        )


class HttpStateChangeError(HttpCustomExceptionBase):
    """Thrown when the requested box state transition is not permitted."""

    exception_id = "invalidStateChange"

    def __init__(self, *, status_code: int = 409):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="The requested state change is invalid.",
            data={},
        )


class HttpBoxVersionError(HttpCustomExceptionBase):
    """Thrown when a request references an outdated resource version."""

    exception_id = "boxVersionOutdated"

    def __init__(self, *, status_code: int = 409):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="The resource version is out of date.",
            data={},
        )


class HttpBoxStateError(HttpCustomExceptionBase):
    """Thrown when an operation is incompatible with the box's current state."""

    exception_id = "boxStateError"

    class DataModel(BaseModel):
        """Model for exception data"""

        state: str

    def __init__(self, *, state: str, status_code: int = 409):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=f"A box in the '{state}' state cannot be deleted.",
            data={"state": state},
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


class HttpGrantNotFoundError(HttpCustomExceptionBase):
    """Thrown when an upload access grant with given ID could not be found."""

    exception_id = "grantNotFound"

    class DataModel(BaseModel):
        """Model for exception data"""

        grant_id: UUID4

    def __init__(self, *, grant_id: UUID4, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=(f"Upload access grant with ID {grant_id} not found."),
            data={"grant_id": str(grant_id)},
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


class HttpIncompleteUploadsError(HttpCustomExceptionBase):
    """Thrown when locking a box is rejected because files still have incomplete uploads."""

    exception_id = "incompleteUploads"

    class DataModel(BaseModel):
        """Model for exception data"""

        incomplete_uploads: list[UUID4]

    def __init__(
        self,
        *,
        incomplete_uploads: list[UUID4],
        status_code: int = 409,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="Cannot lock box: some files still have incomplete uploads.",
            data={"incomplete_uploads": [str(fid) for fid in incomplete_uploads]},
        )


class HttpInternalError(HttpCustomExceptionBase):
    """Thrown for otherwise unhandled exceptions"""

    exception_id = "internalError"

    def __init__(
        self,
        *,
        message: str = "An internal server error has occurred.",
        status_code: int = 500,
    ):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=message,
            data={},
        )
