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

"""Configuration of the core user registry."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings

from ..models.users import UserStatus

INITIAL_USER_STATUS = UserStatus.ACTIVE

__all__ = ["INITIAL_USER_STATUS", "UserRegistryConfig"]


class UserRegistryConfig(BaseSettings):
    """Configuration for the user registry."""

    max_iva_verification_attempts: int = Field(
        default=10, description="Maximum number of verification attempts for an IVA"
    )
