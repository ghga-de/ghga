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

"""DTOs used by the auth adapter API"""

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_serializer

__all__ = ["CreateTOTPToken", "TOTPTokenResponse", "VerifyTOTP"]


class BaseDto(BaseModel):
    """Base model pre-configured for use as Dto."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class CreateTOTPToken(BaseDto):
    """Request model for creating a TOTP token."""

    user_id: str = Field(default=..., title="User ID")
    force: bool = Field(default=False, title="Overwrite existing token")


class TOTPTokenResponse(BaseDto):
    """Response model for a created TOTP token."""

    uri: SecretStr = Field(default=..., title="Provisioning URI")

    @field_serializer("uri", when_used="json")
    def dump_secret(self, v):
        """Serialize the provisioning URI to a string."""
        return v.get_secret_value()


class VerifyTOTP(BaseDto):
    """Request model for verifying a TOTP code."""

    user_id: str = Field(default=..., title="User ID")
    totp: str = Field(default=..., title="the TOTP code to verify")
