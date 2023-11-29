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

"""Models for describing and working with datapack definitions."""

import typing
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError
from typing_extensions import TypeAlias

SupportedDataPackVersions = Literal["0.1.0"]
SUPPORTED_DATA_PACK_VERSIONS = typing.get_args(SupportedDataPackVersions)

ClassName: TypeAlias = str
ResourceId: TypeAlias = str
RelationName: TypeAlias = str


class RootResource(BaseModel):
    """A model for describing the root resource of a datapack."""

    class_name: ClassName = Field(
        ...,
        description="The name of the class of the root resource.",
    )
    resource_id: ResourceId = Field(
        ...,
        description="The ID of the root resource.",
    )


class NoExtraBaseModel(BaseModel):
    """A BaseModel that does not allow any extra fields."""

    model_config = ConfigDict(use_enum_values=True, extra="forbid")


class Resource(NoExtraBaseModel):
    """A model defining content and relations of a resource
    of a specific class.
    """

    content: dict[str, Any] = Field(
        ...,
        description=(
            "The content of the resource that complies with the content schema defined"
            + " in the corresponding schemapack."
        ),
    )

    relations: dict[RelationName, Union[ResourceId, list[ResourceId]]] = Field(
        {},
        description=(
            "A dictionary containing the relations of the resource to other resources."
            + " Each key correspond to the name of a relation property as per the"
            + " schemapack definition. Each value is either a single resource ID (in"
            + " case of many_to_one or one_to_one relations) or a list or resource IDs"
            + " (in case of one_to_many or many_to_many relations)."
        ),
    )


class DataPack(NoExtraBaseModel):
    """A model for describing a schemapack definition."""

    datapack: SupportedDataPackVersions = Field(
        ...,
        description=(
            "Has two purposes: (1) it clearly identifies a YAML/JSON document as"
            + " a datapack definition and (2) it specifies the used version of the"
            + " datapack specification."
        ),
    )

    resources: dict[ClassName, dict[ResourceId, Resource]] = Field(
        ...,
        description=(
            "A nested dictionary containing resources per class name (keys on the first"
            + " level) and resource ID (keys on the second level). Each class defined"
            + " in the schemapack must be present even if no resources are defined for"
            + " it in this datapack."
        ),
    )

    root: Optional[RootResource] = Field(
        None,
        description=(
            "Optionally, a datapack can be rooted to a specific resource. This means"
            + " that the datapack must only contain resources references by the root"
            + " resource as well as the root resource itself."
        ),
    )

    @model_validator(mode="after")
    def check_root_existence(self) -> "DataPack":
        """Make sure that the root resource exists in the datapack."""
        if self.root:
            if self.root.class_name not in self.resources:
                raise PydanticCustomError(
                    "RootClassNotFoundError",
                    (
                        "Root resource class '{class_name}' does not exist in"
                        + " the datapack."
                    ),
                    {
                        "class_name": self.root.class_name,
                    },
                )
            if self.root.resource_id not in self.resources[self.root.class_name]:
                raise PydanticCustomError(
                    "RootResourceNotFoundError",
                    (
                        "Root resource with ID '{resource_id}' does not exist"
                        + " in the datapack."
                    ),
                    {
                        "resource_id": self.root.resource_id,
                    },
                )
        return self
