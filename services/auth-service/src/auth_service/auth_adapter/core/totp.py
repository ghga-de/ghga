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
#

"""TOTP (Time-based One-Time Password) functionality."""

import base64
import hashlib
from enum import Enum
from typing import Annotated, Optional

# nacl is used for encryption of TOTP secrets
# this library is used anyway by the service commons, so no additional dependency
import nacl.secret
import nacl.utils

# pyotp is used for TOTP code generation and verification
# this library is very simple and could also implemented directly if necessary
import pyotp
from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc
from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings

from ..ports.totp import TOTPHandlerPort

__all__ = ["TOTPAlgorithm", "TOTPConfig", "TOTPHandler", "TOTPToken"]


class TOTPAlgorithm(str, Enum):
    """Hash algorithm used for TOTP code generation"""

    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"


class TOTPConfig(BaseSettings):
    """Configuration parameters for TOTP management.

    The default settings are those used by Google Authenticator.
    """

    totp_issuer: str = Field(
        default="GHGA", description="Issuer name for TOTP provisioning URIs"
    )
    totp_image: Optional[AnyHttpUrl] = Field(
        default=None,
        description="URL of the PNG image provided in the TOTP provisioning URIs",
        examples=["https://www.ghga.de/logo.png"],
    )
    totp_algorithm: TOTPAlgorithm = Field(
        default=TOTPAlgorithm.SHA1,
        description="Hash algorithm used for TOTP code generation",
    )
    totp_digits: Annotated[
        int,
        Field(
            ge=6,
            le=12,
            description="Number of digits used for the TOTP code",
        ),
    ] = 6
    totp_interval: Annotated[
        int,
        Field(
            ge=10,
            le=300,
            description="Time interval in seconds for generating TOTP codes",
        ),
    ] = 30
    totp_tolerance: Annotated[
        int,
        Field(
            ge=0,
            le=10,
            description="Number of intervals to check before and after the current time",
        ),
    ] = 1
    totp_attempts: Annotated[
        int,
        Field(
            ge=1,
            le=10,
            description="Maximum number of attempts to verify a TOTP code",
        ),
    ] = 3
    totp_secret_size: Annotated[
        int,
        Field(
            ge=24,
            le=256,
            description="Size of the Base32 encoded TOTP secrets",
        ),
    ] = 32
    # the encryption key is optional since it is only needed by the auth adapter
    totp_encryption_key: Optional[SecretStr] = Field(
        default=None, description="Base64 encoded key used to encrypt TOTP secrets"
    )


class TOTPToken(BaseModel):
    """A TOTP token"""

    # note: not using SecretStr here because the secret is encrypted
    # and we need to store it in the database as a string
    encrypted_secret: str = Field(
        default=...,
        description="Base64 encoded encrypted TOTP secret"
        " which is itself Base32 encoded",
    )
    counter: int = Field(
        default=-1, description="Last used counter for TOTP generation"
    )
    attempts: int = Field(
        default=-1,
        description="Number of attempts to verify the TOTP."
        " 0 means no attempts so far, -1 means successful verification.",
    )

    model_config = {"extra": "forbid"}


class TOTPHandler(TOTPHandlerPort[TOTPToken]):
    """Handler for managing and using TOTP tokens."""

    def __init__(self, config: TOTPConfig):
        self.config = config
        self.issuer = config.totp_issuer
        self.image = config.totp_image
        algorithm = config.totp_algorithm
        if algorithm == TOTPAlgorithm.SHA1:
            self.digest = hashlib.sha1
        elif algorithm == TOTPAlgorithm.SHA256:
            self.digest = hashlib.sha256
        elif algorithm == TOTPAlgorithm.SHA512:
            self.digest = hashlib.sha512
        else:
            raise ValueError(f"Unsupported TOTP algorithm: {algorithm}")
        self.digits = config.totp_digits
        self.interval = config.totp_interval
        self.tolerance = config.totp_tolerance
        self.max_attempts = config.totp_attempts
        self.secret_size = config.totp_secret_size
        encryption_key = config.totp_encryption_key
        if not encryption_key:
            raise ValueError("TOTP encryption key is missing")
        self._secret_box = nacl.secret.SecretBox(
            base64.b64decode(encryption_key.get_secret_value())
        )

    @classmethod
    def random_encryption_key(cls) -> str:
        """Generate random Base64 key of given size for encrypting secrets."""
        key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
        return base64.b64encode(key).decode("ascii")

    def get_secret(self, token: TOTPToken) -> str:
        """Get the decrypted Base32 encoded secret from a TOTP token."""
        encrypted_secret = base64.b64decode(token.encrypted_secret)
        return self._secret_box.decrypt(encrypted_secret).decode("ascii")

    def get_provisioning_uri(self, token: TOTPToken, name: Optional[str]) -> str:
        """Get the provisioning URI for a TOTP token and the given user name."""
        totp = pyotp.TOTP(
            self.get_secret(token),
            digest=self.digest,
            digits=self.digits,
            interval=self.interval,
            issuer=self.issuer,
            name=name,
        )
        return totp.provisioning_uri(image=str(self.image) if self.image else None)

    def generate_token(self) -> TOTPToken:
        """Generate a TOTP token."""
        nonce = nacl.utils.random(self._secret_box.NONCE_SIZE)
        decrypted_secret = pyotp.random_base32(self.secret_size).encode("ascii")
        encrypted_secret_bytes = self._secret_box.encrypt(decrypted_secret, nonce)
        encrypted_secret = base64.b64encode(encrypted_secret_bytes).decode("ascii")
        return TOTPToken(encrypted_secret=encrypted_secret)

    def generate_code(
        self,
        token: TOTPToken,
        for_time: Optional[UTCDatetime] = None,
        counter_offset: int = 0,
    ) -> str:
        """Generate a TOTP code for testing purposes."""
        totp = pyotp.TOTP(
            self.get_secret(token),
            digest=self.digest,
            digits=self.digits,
            interval=self.interval,
        )
        if for_time is None:
            for_time = now_as_utc()
        return totp.at(for_time, counter_offset)

    def verify_code(
        self,
        token: TOTPToken,
        code: str,
        for_time: Optional[UTCDatetime] = None,
    ) -> Optional[bool]:
        """Verify a TOTP token with replay attack prevention and rate limiting.

        A return value of True means that the code is valid.
        If the return value is None, the usage parameters of the token have
        been changed and the token should be saved back to the database.
        """
        if not code or len(code) != self.digits or not code.isdigit():
            # totally invalid codes are rejected immediately,
            # and they don't increase the number of attempts
            return None
        totp = pyotp.TOTP(
            self.get_secret(token),
            digest=self.digest,
            digits=self.digits,
            interval=self.interval,
        )
        # get the current TOTP counter
        if for_time is None:
            for_time = now_as_utc()
        counter = totp.timecode(for_time)
        if token.counter > counter:
            # token has been used in the future (should never happen)
            return None
        if token.counter < counter:
            # first attempt with this counter
            token.counter = counter
            token.attempts = 0
        elif not 0 <= token.attempts < self.max_attempts:
            # token has already been verified (replay attack)
            # or has reached the maximum number of attempts (brute force attack)
            return None
        verified = totp.verify(code, for_time=for_time, valid_window=self.tolerance)
        if verified:
            token.attempts = -1  # mark token as verified
        else:
            token.attempts += 1  # memorize the number of attempts
        return verified
