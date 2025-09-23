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

from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, BaseModel


class S3UploadDetails(BaseModel):
    """Class for linking a multipart upload to its FileUpload object"""

    file_id: UUID4  # the id of the corresponding FileUpload
    storage_alias: str
    s3_upload_id: str
    initiated: UTCDatetime
    completed: UTCDatetime | None = None
