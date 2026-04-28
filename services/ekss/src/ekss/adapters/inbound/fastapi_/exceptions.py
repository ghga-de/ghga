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
"""Defines exceptions that can occur during envelope data extraction"""

from ghga_service_commons.httpyexpect.server import HttpCustomExceptionBase
from pydantic import BaseModel


class HttpSecretInsertionError(HttpCustomExceptionBase):
    """Raised when a secret could not be inserted into the vault"""

    exception_id = "secretInsertionError"

    class DataModel(BaseModel):
        """Model for exception data"""

    def __init__(self, *, status_code: int = 502):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=("Could not insert key into vault"),
            data={},
        )


class HttpSecretNotFoundError(HttpCustomExceptionBase):
    """Raised when no secret with the given id could be found"""

    exception_id = "secretNotFoundError"

    class DataModel(BaseModel):
        """Model for exception data"""

    def __init__(self, *, status_code: int = 404):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="The secret for the given id was not found.",
            data={},
        )


class HttpDecodingError(HttpCustomExceptionBase):
    """Raised when a byte string could not be decoded using base64"""

    exception_id = "decodingError"

    def __init__(self, *, affected: str, status_code: int = 422):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=f"Could not decode the given string as base64: {affected}",
            data={},
        )


class HttpDecryptionError(HttpCustomExceptionBase):
    """Raised when the submitted file secret could not be decrypted"""

    exception_id = "decryptionError"

    def __init__(self, *, status_code: int = 403):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="Could not decrypt the submitted file secret",
            data={},
        )


class HttpSecretDeletionError(HttpCustomExceptionBase):
    """Raised when a secret was found but could not be deleted"""

    exception_id = "secretDeletionError"

    class DataModel(BaseModel):
        """Model for exception data"""

    def __init__(self, *, status_code: int = 500):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="The secret was found but could not be deleted.",
            data={},
        )


class HttpEnvelopeCreationError(HttpCustomExceptionBase):
    """Raised when a Crypt4GH envelope could not be created for the requested secret"""

    exception_id = "envelopeCreationError"

    class DataModel(BaseModel):
        """Model for exception data"""

    def __init__(self, *, status_code: int = 500):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description="Could not create envelope for the requested secret",
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
