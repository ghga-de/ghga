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

"""REST API-specific data models (not used by core package)"""

from pydantic import ConfigDict

try:  # workaround for https://github.com/pydantic/pydantic/issues/5821
    from typing_extensions import Literal
except ImportError:
    from typing import Literal  # type: ignore

from pydantic import BaseModel, Field

# shortcuts:
# pylint: disable=unused-import
from ucs.core.models import FileMetadata, UploadAttempt, UploadStatus  # noqa: F401


class UploadAttemptCreation(BaseModel):
    """Properties required to create a new upload."""

    file_id: str = Field(
        ..., description="The ID of the file corresponding to this upload."
    )
    submitter_public_key: str = Field(
        ..., description="The public key used by the submittter to encrypt the file."
    )
    storage_alias: str = Field(
        ...,
        description="Alias identifying the object storage location to use for this upload",
    )
    model_config = ConfigDict(title="Properties required to create a new upload")


class UploadAttemptUpdate(BaseModel):
    """Request body to update an existing mutli-part upload."""

    status: Literal["uploaded", "cancelled"]
    model_config = ConfigDict(title="Multi-Part Upload Update")


class PartUploadDetails(BaseModel):
    """Contains details for uploading the bytes of one file part."""

    url: str = Field(
        ...,
        description=(
            "A fully resolvable URL that can be used to upload the actual"
            + " object bytes for one upload part."
        ),
    )
