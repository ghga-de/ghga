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

"""Model classes for configuring the claims repository."""

from pydantic import Field

from auth_service.user_management.user_registry.models.ivas import IvaType

from . import BaseDto

__all__ = ["IvaType", "UserWithIVA"]


class UserWithIVA(BaseDto):
    """User with external ID and associated IVA."""

    ext_id: str = Field(default=..., description="The external ID of the user")
    name: str = Field(default=..., description="The full name of the user")
    email: str = Field(default=..., description="The email address of the user")
    iva_type: IvaType = Field(
        default=..., description="The type of the validation address of the user"
    )
    iva_value: str = Field(
        default=..., description="The actual validation address of the user"
    )
