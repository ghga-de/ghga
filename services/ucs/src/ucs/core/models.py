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

"""Defines dataclasses for holding business-logic data"""

from ghga_event_schemas import pydantic_ as event_schemas
from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, BaseModel, Field


class S3UploadDetails(BaseModel):
    """Class for linking a multipart upload to its FileUpload object"""

    file_id: UUID4  # the id of the corresponding FileUpload
    bucket_id: str
    object_id: UUID4  # the S3 object ID (from FileUpload.object_id)
    storage_alias: str
    s3_upload_id: str
    initiated: UTCDatetime
    completed: UTCDatetime | None = None


class FileUploadBox(event_schemas.FileUploadBox):
    """A class representing a box that bundles files belonging to the same upload."""


class ResearchDataUploadBox(event_schemas.ResearchDataUploadBox):
    """A class representing a ResearchDataUploadBox."""


class FileUpload(event_schemas.FileUpload):
    """A FileUpload.

    Contains all information required for a file's journey from upload initiation to
    permanent archival.
    """

    inbox_upload_completed: bool = Field(  # Note: This is a UCS-only field
        default=False,
        description="Indicates whether the file has been completely uploaded to the inbox.",
    )
