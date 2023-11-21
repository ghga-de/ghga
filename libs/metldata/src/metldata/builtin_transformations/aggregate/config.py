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

"""Config for aggregate transformations"""

from typing import Optional

from pydantic import BaseModel, model_validator
from pydantic_settings import BaseSettings

from metldata.builtin_transformations.aggregate.func import (
    AggregationFunction,
    transformation_by_name,
)


class AggregationOperation(BaseModel):
    """A model for a single aggregation operation executed on one or multiple
    branches in the data described by a path in the model.
    """

    input_paths: list[str]
    output_path: str
    visit_only_once: Optional[list[str]] = None
    function: type[AggregationFunction]

    @model_validator(mode="before")
    def lookup_operation(cls, values: dict) -> dict:
        """Replaces operation strings with operation types."""
        if "function" in values:
            values["function"] = transformation_by_name(values["function"])
        # not raising an error otherwise as pydantic will do that in following
        # validation
        return values


class Aggregation(BaseModel):
    """Model for an aggregation."""

    input: str
    output: str
    operations: list[AggregationOperation]


class AggregateConfig(BaseSettings):
    """A model for the configuration of the aggregate transformation."""

    aggregations: list[Aggregation]
