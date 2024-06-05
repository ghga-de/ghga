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
"""Defines exceptions that can occur during envelope data extraction"""

from ghga_service_commons.httpyexpect.server import HttpCustomExceptionBase
from pydantic import BaseModel


class HttpMalformedOrMissingEnvelopeError(HttpCustomExceptionBase):
    """Thrown when envelope decryption fails due to a missing or malformed envelope."""

    exception_id = "malformedOrMissingEnvelopeError"

    class DataModel(BaseModel):
        """Model for exception data"""

    def __init__(self, *, status_code: int = 400):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=("Envelope malformed or missing"),
            data={},
        )


class HttpEnvelopeDecryptionError(HttpCustomExceptionBase):
    """Thrown when no available secret crypt4GH key can successfully decrypt the file envelope."""

    exception_id = "envelopeDecryptionError"

    class DataModel(BaseModel):
        """Model for exception data"""

    def __init__(self, *, status_code: int = 403):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=("Could not decrypt envelope content with given keys"),
            data={},
        )


class HttpSecretInsertionError(HttpCustomExceptionBase):
    """Thrown when a secret could not be inserted into the vault"""

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


class HttpVaultConnectionError(HttpCustomExceptionBase):
    """Thrown when the EKSS could not connect to the vault"""

    exception_id = "vaultConnectionError"

    class DataModel(BaseModel):
        """Model for exception data"""

    def __init__(self, *, status_code: int = 504):
        """Construct message and init the exception."""
        super().__init__(
            status_code=status_code,
            description=("Could not connect to vault"),
            data={},
        )


class HttpSecretNotFoundError(HttpCustomExceptionBase):
    """Thrown when no secret with the given id could be found"""

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
