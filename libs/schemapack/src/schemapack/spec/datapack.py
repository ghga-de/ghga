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

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import TypeAlias

SupportedDataPackVersions = Literal["0.1.0"]
SUPPORTED_DATA_PACK_VERSIONS = typing.get_args(SupportedDataPackVersions)

ClassName: TypeAlias = str
ResourceId: TypeAlias = str
RelationName: TypeAlias = str


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

    root: Optional[ResourceId] = Field(
        None,
        description=(
            "The ID of the root resource which must be of the class defined as root"
            + " in the schemapack. This must and may be only specified if the"
            + " schemapack is rooted."
        ),
    )
