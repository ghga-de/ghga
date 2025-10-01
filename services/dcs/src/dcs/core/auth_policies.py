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
"""Supported authentication policies for endpoints"""

from typing import Literal

from ghga_service_commons.utils.crypt import decode_key
from pydantic import BaseModel, Field, field_validator


class WorkOrderContext(BaseModel):
    """Work order token model"""

    work_type: Literal["download"] = Field(
        default=..., title="Type", description="Work type"
    )
    file_id: str = Field(
        default=...,
        title="File ID",
        description="The ID of the file that shall be downloaded or uploaded",
    )
    user_public_crypt4gh_key: str = Field(
        ..., description="Base64 encoded Crypt4GH public key of the user"
    )

    @field_validator("user_public_crypt4gh_key")
    @classmethod
    def validate_crypt4gh_key(cls, pubkey):
        """Make sure the received pubkey is decodable"""
        decode_key(pubkey)
        return pubkey
