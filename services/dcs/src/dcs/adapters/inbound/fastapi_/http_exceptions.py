# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from ghga_service_commons.httpyexpect.server.exceptions import HttpCustomExceptionBase
from pydantic import BaseModel


class HttpEnvelopeNotFoundError(HttpCustomExceptionBase):
    """Thrown when envelope data is not found."""

    exception_id = "envelopeNotFoundError"

    def __init__(self, *, description: str, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=description,
            data={},
        )


class HttpInternalServerError(HttpCustomExceptionBase):
    """Thrown when an error is raised with details that should not be propagated to a client"""

    exception_id = "internalServerError"

    def __init__(self, *, status_code: int = 500):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code, description="Internal Server Error.", data={}
        )


class HttpExternalAPIError(HttpCustomExceptionBase):
    """Thrown when communication with an external API produces an error"""

    exception_id = "externalAPIError"

    def __init__(self, *, description: str, status_code: int = 500):
        """Construct message and init the exception."""
        super().__init__(status_code=status_code, description=description, data={})


class HttpObjectNotFoundError(HttpCustomExceptionBase):
    """Thrown when a file with given ID could not be found."""

    exception_id = "noSuchObject"

    class DataModel(BaseModel):
        """Model for exception data"""

        object_id: str

    def __init__(self, *, object_id: str, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="The requested DrsObject wasn't found",
            data={"object_id": object_id},
        )


class HttpWrongFileAuthorizationError(HttpCustomExceptionBase):
    """Raised when a work order token cannot be validated"""

    exception_id = "wrongFileAuthorizationError"

    def __init__(self, *, status_code: int = 403):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="Endpoint file ID did not match file ID announced in work order token.",
            data={},
        )
