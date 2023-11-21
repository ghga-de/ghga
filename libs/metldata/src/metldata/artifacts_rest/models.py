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

"""Data models."""

from typing import Optional

from ghga_service_commons.utils.utc_dates import DateTimeUTC
from pydantic import BaseModel, Field, field_validator
from typing_extensions import TypedDict

from metldata.custom_types import Json
from metldata.model_utils.anchors import AnchorPoint

try:  # workaround for https://github.com/pydantic/pydantic/issues/5821
    from typing_extensions import Literal
except ImportError:
    from typing import Literal  # type: ignore


class ArtifactResource(BaseModel):
    """Information on a resource of an artifact."""

    id_: str = Field(..., description="The ID of the resource.")
    class_name: str = Field(
        ..., description="The name of the class this resource corresponds to."
    )
    content: Json = Field(..., description="The metadata content of that resource.")


class ArtifactResourceClass(BaseModel):
    """Model to describe a resource class of an artifact."""

    name: str = Field(..., description="The name of the metadata class.")
    description: Optional[str] = Field(
        None, description="A description of the metadata class."
    )
    anchor_point: AnchorPoint = Field(
        ..., description="The anchor point for this metadata class."
    )
    json_schema: Json = Field(
        ..., description="The JSON schema for this metadata class."
    )


class ArtifactInfo(BaseModel):
    """Model to describe general information on an artifact.
    Please note, it does not contain actual artifact instances derived from specific
    metadata.
    """

    name: str = Field(..., description="The name of the artifact.")
    description: str = Field(..., description="A description of the artifact.")

    resource_classes: dict[str, ArtifactResourceClass] = Field(
        ...,
        description=(
            "A dictionary of resource classes for this artifact."
            + " The keys are the names of the classes."
            + " The values are the corresponding class models."
        ),
    )

    @field_validator("resource_classes")
    def check_resource_class_names(
        cls, value: dict[str, ArtifactResourceClass]
    ) -> dict[str, ArtifactResourceClass]:
        """Check if the keys of the `resource_classes` dictionary correspond to the
        names of the metadata classes.
        """
        for class_name, resource_class in value.items():
            if class_name != resource_class.name:
                raise ValueError(
                    f"Key '{class_name}' of 'resource_classes' does not match"
                    + f" the name '{resource_class.name}' of the corresponding"
                    + " metadata class."
                )

        return value


class ResourceCount(TypedDict):
    """Number of instances of a resource."""

    count: int


class ValueCount(ResourceCount):
    """Number of instances of a certain value."""

    value: str


class ResourceStats(ResourceCount, total=False):
    """Summary statistics for a resource."""

    stats: dict[str, list[ValueCount]]


class GlobalStats(BaseModel):
    """Model to describe statistical information on all resources."""

    id: Literal["global"]
    created: DateTimeUTC = Field(..., description="When these stats were created.")

    resource_stats: dict[str, ResourceStats] = Field(
        ...,
        description=(
            "A dictionary of global resource stats."
            + " The keys are the names of the classes."
            + " The values are the corresponding summary statistics."
        ),
    )
