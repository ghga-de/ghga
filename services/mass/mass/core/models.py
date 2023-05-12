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

"""Defines dataclasses for holding business-logic data"""

from hexkit.custom_types import JsonObject
from pydantic import BaseModel, Field


class SearchableClass(BaseModel):
    """Represents a searchable artifact or resource type"""

    description: str = Field(
        ..., description="A brief description of the resource type"
    )
    facetable_properties: list[str] = Field(
        ..., description="A list of of the facetable properties for the resource type"
    )


class Resource(BaseModel):
    """Represents an artifact or resource class such as a Dataset, Sample, Study, etc."""

    id_: str = Field(..., description="The identifier for this resource")
    content: JsonObject = Field(..., description="The actual content of the resource")


class Filter(BaseModel):
    """Represents a filter used to refine results"""

    key: str = Field(..., description="The field to filter")
    value: str = Field(..., description="The value the field must match")
