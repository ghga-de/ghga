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

"""Config parameters."""

from typing import cast

from pydantic import Field

from ghga_service_commons.api import ApiConfigBase
from ghga_service_commons.auth.ghga import AuthConfig
from ghga_service_commons.utils.jwt_helpers import generate_jwk

__all__ = ["Config"]

# create a key pair for signing and validating JSON web tokens
AUTH_KEY_PAIR = generate_jwk()


class Config(ApiConfigBase, AuthConfig):
    """Config parameters and their defaults."""

    auth_key: str = Field(
        default=cast(str, AUTH_KEY_PAIR.export(private_key=False)),
        description="The GHGA internal public key for validating the token signature.",
    )
