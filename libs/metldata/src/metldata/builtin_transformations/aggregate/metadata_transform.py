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

from metldata.builtin_transformations.aggregate.cached_model import CachedMetadataModel
from metldata.builtin_transformations.aggregate.config import Aggregation
from metldata.builtin_transformations.aggregate.data_subgraph import DataSubgraph
from metldata.builtin_transformations.aggregate.expanding_dict import ExpandingDict
from metldata.builtin_transformations.aggregate.func import MetadataTransformationError
from metldata.custom_types import Json
from metldata.model_utils.anchors import AnchorPoint


# pylint: disable=unused-argument
def execute_aggregation(
    *,
    original_model: CachedMetadataModel,
    original_data: Json,
    aggregation: Aggregation,
) -> list[Json]:
    """Transforms the metadata according to the specified aggregation operation."""
    anchor_point = original_model.anchors_points_by_target[aggregation.input]
    id_slot = anchor_point.identifier_slot
    input_anchor_data = original_data[anchor_point.root_slot]
    output_data: list[Json] = []
    for input_element in input_anchor_data:
        result = ExpandingDict()
        for operation in aggregation.operations:
            subgraph = DataSubgraph(
                model=original_model,
                submission_data=original_data,
                origin=aggregation.input,
                path_strings=operation.input_paths,
                visit_once_classes=operation.visit_only_once,
            )
            try:
                aggregated = operation.function.func(
                    subgraph.terminal_nodes(data=input_element)
                )
            except Exception as error:
                raise MetadataTransformationError(
                    "Cannot execute operation:\n"
                    f"{operation}\nwith input {input_element!r}:\n{error}"
                ) from error
            result.set_path_value(operation.output_path, aggregated)
        result[id_slot] = input_element[id_slot]
        output_data.append(result.to_dict())

    return output_data


def execute_aggregations(
    *,
    original_model: CachedMetadataModel,
    transformed_anchors_points: dict[str, AnchorPoint],
    metadata: Json,
    aggregations: list[Aggregation],
) -> Json:
    """Transforms the metadata according to the specified list of aggregation
    operations.
    """
    transformed_data = {}
    for aggregation in aggregations:
        output_data = execute_aggregation(
            original_model=original_model,
            original_data=metadata,
            aggregation=aggregation,
        )
        transformed_data[
            transformed_anchors_points[aggregation.output].root_slot
        ] = output_data
    return transformed_data
