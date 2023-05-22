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
"""Models only used by the API"""
from typing import Optional

from pydantic import BaseModel, Field

from mass.core.models import Filter


class SearchParameters(BaseModel):
    """Represents the data submitted in a search query"""

    class_name: str = Field(
        ..., description="The name of the resource class, e.g. Dataset"
    )
    query: str = Field(default="", description="The keyword search for the query")
    filters: list[Filter] = Field(
        default=[], description="The filters to apply to the search"
    )
    skip: int = Field(
        default=0, description="The number of results to skip for pagination"
    )
    limit: Optional[int] = Field(
        default=None, description="Limit the results to this number"
    )
