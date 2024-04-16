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
#

"""Configuration of the auth context."""

__all__ = ["DemoAuthContext", "DemoAuthConfig"]

from typing import Any, cast

from pydantic import BaseModel, Field

from ghga_service_commons.auth.jwt_auth import JWTAuthConfig
from ghga_service_commons.utils.jwt_helpers import generate_jwk
from ghga_service_commons.utils.utc_dates import UTCDatetime


class DemoAuthContext(BaseModel):
    """Example auth context."""

    name: str = Field(default=..., description="The name of the user")
    expires: UTCDatetime = Field(
        default=..., description="The expiration date of this context"
    )
    is_vip: bool = Field(default=False, description="Whether the user is a VIP")


# create a key pair for signing and validating JSON web tokens
AUTH_KEY_PAIR = generate_jwk()


class DemoAuthConfig(JWTAuthConfig):
    """Config parameters and their defaults for the example auth context."""

    auth_key: str = Field(
        default=cast(str, AUTH_KEY_PAIR.export(private_key=False)),
        description="The public key for validating the token signature.",
    )
    auth_check_claims: dict[str, Any] = Field(
        default={"name": None, "exp": None},
        description="A dict of all claims that shall be verified by the provider."
        + " A value of None means that the claim can have any value.",
    )
    auth_map_claims: dict[str, str] = Field(
        default={"exp": "expires"},
        description="A mapping of claims to attributes in the auth context."
        + " Only differently named attributes must be specified."
        + " The value None can be used to exclude claims from the auth context.",
    )
