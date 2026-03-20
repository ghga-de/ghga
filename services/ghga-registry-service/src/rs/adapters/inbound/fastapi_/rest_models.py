# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""REST request/response models for the GHGA Registry Service."""

from typing import Annotated, Literal

from pydantic import (
    UUID4,
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

from rs.core.models import FileAccession


def _ascii_only(v: str) -> str:
    if not v.isascii():
        raise ValueError("must contain only ASCII characters")
    return v


PID = Annotated[
    str, StringConstraints(min_length=1, max_length=256), AfterValidator(_ascii_only)
]


class FileIdMappingRequest(BaseModel):
    """Request body for posting file ID mappings."""

    study_pid: PID = Field(
        default=...,
        description="Identifier of the study to which the file accessions belong.",
    )
    mapping: dict[FileAccession, UUID4] = Field(
        default=..., description="Map of file accession PIDs to internal file IDs."
    )


class BaseWorkOrderToken(BaseModel):
    """Base model for work order tokens."""

    work_type: str
    model_config = ConfigDict(frozen=True)


class MapFileIdsWorkOrder(BaseWorkOrderToken):
    """Work order token for submitting an accession map."""

    work_type: Literal["map"] = "map"
    user_id: UUID4
    study_pid: PID
