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

"""Model transformation for aggregate transformations."""

from metldata.builtin_transformations.aggregate.config import AggregateConfig
from metldata.model_utils.essentials import MetadataModel


def barebone_model_from_other(model: MetadataModel) -> MetadataModel:
    """Create a new MetadataModel with no classes, enums, slots and subsets. All
    other SchemaDefinition attributes are kept."""
    model_dict = model.as_dict(essential=False)
    del model_dict["classes"]
    del model_dict["enums"]
    del model_dict["slots"]
    del model_dict["subsets"]
    return MetadataModel(**model_dict)


# pylint: disable=unused-argument
def add_aggretation_slots(
    model: MetadataModel, config: AggregateConfig
) -> MetadataModel:
    """Add slots resulting from the aggregations described in the provided config."""
    return model


def create_aggregate_model(model: MetadataModel, config: AggregateConfig):
    """Create data model resulting from aggregations described in the provided config"""
    new_model = barebone_model_from_other(model)
    return add_aggretation_slots(model=new_model, config=config)
