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

"""Metadata transformation functionality for the aggregate transformation."""


from metldata.builtin_transformations.aggregate.config import Aggregation
from metldata.builtin_transformations.aggregate.data_subgraph import DataSubgraph
from metldata.builtin_transformations.aggregate.expanding_dict import ExpandingDict
from metldata.custom_types import Json
from metldata.model_utils.anchors import AnchorPoint
from metldata.model_utils.essentials import MetadataModel


# pylint: disable=unused-argument
def execute_aggregation(
    *,
    original_model: MetadataModel,
    original_data: Json,
    aggregation: Aggregation,
    original_anchors_points: dict[str, AnchorPoint],
) -> list[Json]:
    """Transforms the metadata according to the specified aggregation operation."""
    anchor_point = original_anchors_points[aggregation.input]
    id_slot = anchor_point.identifier_slot
    input_anchor_data = original_data[anchor_point.root_slot]
    subgraphs = [
        DataSubgraph(
            model=original_model,
            submission_data=original_data,
            origin=aggregation.input,
            path_strings=operation.input_paths,
        )
        for operation in aggregation.operations
    ]
    output_data: list[Json] = []
    for input_element in input_anchor_data:
        result = ExpandingDict()
        for operation, subgraph in zip(aggregation.operations, subgraphs):
            aggregated = operation.function.func(
                subgraph.terminal_nodes(data=input_element)
            )
            result.set_path_value(operation.output_path, aggregated)
        result[id_slot] = input_element[id_slot]
        output_data.append(dict(result))

    return output_data


def execute_aggregations(
    *,
    original_model: MetadataModel,
    original_anchors_points: dict[str, AnchorPoint],
    transformed_anchors_points: dict[str, AnchorPoint],
    metadata: Json,
    aggregations: list[Aggregation],
) -> Json:
    """Transforms the metadata according to the specified list of aggregation
    operations."""
    transformed_data = {}
    for aggregation in aggregations:
        output_data = execute_aggregation(
            original_model=original_model,
            original_data=metadata,
            aggregation=aggregation,
            original_anchors_points=original_anchors_points,
        )
        transformed_data[
            transformed_anchors_points[aggregation.output].root_slot
        ] = output_data
    return transformed_data
