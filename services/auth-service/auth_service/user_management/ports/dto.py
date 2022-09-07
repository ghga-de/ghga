# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""DTOs for the user registry"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr

__all__ = ["AcademicTitle", "UserCreationDto", "UserDto"]


class AcademicTitle(str, Enum):
    """Academic title"""

    DR = "Dr."
    PROF = "Prof."


class UserCreationDto(BaseModel):
    """User DTO creation model"""

    ls_id: EmailStr
    name: str
    email: EmailStr

    academic_title: Optional[AcademicTitle]
    research_topics: Optional[str]
    registration_reason: Optional[str]
    registration_date: datetime

    class Config:  # pylint: disable=missing-class-docstring
        frozen = True
        use_enum_values = True


class UserDto(UserCreationDto):
    """User DTO model"""

    id: str  # actually UUID4
