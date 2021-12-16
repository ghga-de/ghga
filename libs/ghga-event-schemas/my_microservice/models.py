# Copyright 2021 Universität Tübingen, DKFZ and EMBL
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

"""Defines all dataclasses/classes pertaining to a data model or schema"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SupportedLanguages = Literal["Greek", "Croatian", "French", "German"]


class MessageBase(BaseModel):
    """A message base container"""

    message: str = Field(..., description="The message content.")
    created_at: datetime = Field(
        ..., description="The date/time when the message was created"
    )


class GreetingBase(BaseModel):
    """A container for basic metadata on a greeting phrase/expression"""

    language: SupportedLanguages = Field(..., description="The language.")
    isinformal: bool = Field(
        ..., description="Is the expression used in informal contexts?"
    )


class GreetingExpression(GreetingBase):
    """A container for describing a greeting expression"""

    expression: str = Field(..., description="The actual greeting expression")


class Greeting(GreetingBase, MessageBase):
    """A container storing a greeting for a specfic person incl. metadata"""

    pass  # pylint: disable=unnecessary-pass
