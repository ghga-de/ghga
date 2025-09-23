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

"""A collection of http exceptions."""

from ghga_service_commons.httpyexpect.server import HttpCustomExceptionBase
from pydantic import UUID4, BaseModel

__all__ = [
    "HttpBoxNotFoundError",
    "HttpGrantNotFoundError",
    "HttpInternalError",
    "HttpNotAuthorizedError",
]


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
