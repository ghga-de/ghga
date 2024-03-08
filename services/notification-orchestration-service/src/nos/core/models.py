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

"""Contains models relevant to the core domain"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class AcademicTitle(str, Enum):
    """Academic title"""

    DR = "Dr."
    PROF = "Prof."


class BaseDto(BaseModel):
    """Base model pre-configured for use as Dto."""

    model_config = {"extra": "forbid", "frozen": True}


class UserData(BaseDto):
    """Basic data of a user"""

    name: str = Field(
        default=...,
        description="Full name of the user",
        examples=["Rosalind Franklin"],
    )
    title: Optional[AcademicTitle] = Field(
        default=None, title="Academic title", description="Academic title of the user"
    )
    email: EmailStr = Field(
        default=...,
        description="Preferred e-mail address of the user",
        examples=["user@home.org"],
    )


class User(UserData):
    """Complete user model with ID"""

    id: str = Field(default=..., description="Internally used ID")  # actually UUID
