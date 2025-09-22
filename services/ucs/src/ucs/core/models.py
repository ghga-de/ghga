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

from typing import Literal

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, BaseModel, model_validator


class FileUploadBox(BaseModel):
    """A class representing a box that bundles files belonging to the same upload"""

    id: UUID4  # unique identifier for the instance
    locked: bool = False  # Whether or not changes to the files in the box are allowed
    file_count: int = 0  # The number of files in the box
    size: int = 0  # The total size of all files in the box
    storage_alias: str


FileUploadState = Literal["init", "inbox", "archived"]
# init = file upload initiated, but not yet finished
# inbox = file upload complete, file in inbox
# archived = file moved out of inbox after completion


class FileUpload(BaseModel):
    """A File Upload"""

    id: UUID4  # unique identifier for the instance
    completed: bool = False  # whether or not the file upload has finished
    state: FileUploadState = "init"
    alias: str  # the submitted alias from the metadata (unique within the box)
    box_id: UUID4
    checksum: str
    size: int

    @model_validator(mode="after")
    def validate_completed(self):
        """Make sure `completed` and `state` are in sync."""
        if self.completed != (self.state in ["inbox", "archived"]):
            raise ValueError(
                "Completed must be False if state is 'init' and True otherwise."
            )
        return self


class S3UploadDetails(BaseModel):
    """Class for linking a multipart upload to its FileUpload object"""

    file_id: UUID4  # the id of the corresponding FileUpload
    storage_alias: str
    s3_upload_id: str
    initiated: UTCDatetime
    completed: UTCDatetime | None = None


class FileUploadReport(BaseModel):
    """A report that models the result of the Data Hub-side file inspection"""

    # Note, this model is subject to change; consider this a rough sketch for now
    file_id: UUID4
    secret_id: str
    passed_inspection: bool
