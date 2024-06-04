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

"""Defines dataclasses for business-logic data as well as request/reply models for use
in the api.
"""

import re
from typing import Literal

from ghga_service_commons.utils import utc_dates
from pydantic import BaseModel, field_validator


class AccessURL(BaseModel):
    """AccessUrl object for access method"""

    url: str


class AccessMethod(BaseModel):
    """Wrapped DRS access_methods field value"""

    access_url: AccessURL
    type: Literal["s3"] = "s3"


class Checksum(BaseModel):
    """Wrapped DRS checksums field value"""

    checksum: str
    type: Literal["sha-256"] = "sha-256"


class DrsObjectBase(BaseModel):
    """A model containing the metadata needed to register a new DRS object."""

    file_id: str
    decryption_secret_id: str
    decrypted_sha256: str
    decrypted_size: int
    creation_date: str
    s3_endpoint_alias: str


class DrsObject(DrsObjectBase):
    """A DrsObjectBase with the object_id generated"""

    object_id: str


class AccessTimeDrsObject(DrsObject):
    """DRS Model with information for outbox caching strategy"""

    last_accessed: utc_dates.UTCDatetime


class DrsObjectWithUri(DrsObject):
    """A model for describing DRS object metadata including a self URI."""

    self_uri: str

    @field_validator("self_uri")
    @classmethod
    def check_self_uri(cls, value: str):
        """Checks if the self_uri is a valid DRS URI."""
        if not re.match(r"^drs://.+/.+", value):
            raise ValueError(f"The self_uri '{value}' is no valid DRS URI.")

        return value


class DrsObjectWithAccess(DrsObjectWithUri):
    """A model for describing DRS object metadata including information on how to access
    its content.
    """

    access_url: str

    def convert_to_drs_response_model(self, size: int):
        """Convert from internal representation ingested by even to DRS compliant representation"""
        access_method = AccessMethod(access_url=AccessURL(url=self.access_url))
        checksum = Checksum(checksum=self.decrypted_sha256)

        return DrsObjectResponseModel(
            access_methods=[access_method],
            checksums=[checksum],
            created_time=self.creation_date,
            id=self.file_id,
            self_uri=self.self_uri,
            size=size,
        )


class DrsObjectResponseModel(BaseModel):
    """A DRS compliant representation for the DrsObjectWithAccess model"""

    access_methods: list[AccessMethod]
    checksums: list[Checksum]
    created_time: str
    id: str
    self_uri: str
    size: int
