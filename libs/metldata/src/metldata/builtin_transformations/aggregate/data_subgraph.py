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

"""This module provides the DataSubgraph class to traverse a subgraph of a
LinkML-based JSON data graph.
"""

from collections import defaultdict
from collections.abc import Iterator
from typing import Any, Optional

from linkml_runtime.linkml_model import SlotDefinition

from metldata.builtin_transformations.aggregate.cached_model import CachedMetadataModel
from metldata.custom_types import Json
from metldata.metadata_utils import get_resource_dict_of_class
from metldata.model_utils.anchors import AnchorPoint
from metldata.model_utils.essentials import MetadataModel


class DataTraversalError(RuntimeError):
    """Error raised when JSON data cannot be traversed as expected."""


def _resolve_path(
    *, model: MetadataModel, all_classes: list[str], origin: str, slot_names: list[str]
) -> list[SlotDefinition]:
    cur_cls = origin
    resolved_path = []
    for slot_name in slot_names:
        if cur_cls is None:
            raise DataTraversalError(
                f"Unable to resolve path '{slot_names}': Cannot traverse beyond"
                f" '{slot_names[len(resolved_path)]}', range is type or enum."
            )
        try:
            slot_def = model.schema_view.induced_slot(slot_name, cur_cls)
        except ValueError as error:
            raise DataTraversalError(
                f"Unable to find slot '{slot_name}' for class '{cur_cls}'."
            ) from error
        resolved_path.append(slot_def)
        cur_cls = slot_def.range if slot_def.range in all_classes else None
    return resolved_path


class DataSubgraph:
    """
    Given that LinkML models enable references between objects, any JSON data
    structured according to a LinkML model can be treated as a connected graph
    of objects, i.e. a data graph. A DataSubgraph represents a subgraph of the
    object graph described by a set of paths in the entity relationship model of
    the LinkML schema. Note that a path in the entity relationship model
    corresponds to a subgraph in the data graph, since the entity relationships
    can have various cardinalities (i.e. LinkML slots may be multivalued).

    The DataSubgraph enables to iterate through the nodes of the subgraph.
    """

    _model: MetadataModel
    _paths: list[list[SlotDefinition]]
    _class_identifiers: dict[str, Optional[str]]
    _all_classes: list[str]
    _anchor_points: dict[str, AnchorPoint]

    def _get_class_identifier(self, class_name: str) -> str:
        """Returns the identifier slot name for the given class name.

        Args:
            class_name (str): Name of the class

        Raises:
            DataTraversalError: If the class is unknown or does not have an
            identifier slot

        Returns:
            str: The name of the identifier slot.
        """
        slot_name = self._class_identifiers[class_name]
        if slot_name is None:
            raise DataTraversalError(
                f"Identifier slot for class '{class_name}' not found."
            )
        return slot_name

    def _resolve_non_inlined(
        self, *, identifiers: list[Any], class_name: str
    ) -> list[Json]:
        """Resolves a list of identifiers to the corresponding objects based on
        the provided class name.

        Args:
            identifiers (list[Any]): A list of identifiers
            class_name (str): The name of the corresponding class

        Raises:
            DataTraversalError: Raised when an identifier cannot be resolved.

        Returns:
            list[Json]: A list of objects corresponding to the identifiers.
        """
        try:
            return [
                self._resources_by_id[class_name][next_node]
                for next_node in identifiers
            ]
        except KeyError as error:
            raise DataTraversalError(
                f"Unable to resolve ID '{error.args[0]}' for class '{class_name}'"
            ) from error

    def terminal_nodes(self, data: Json) -> Iterator[Any]:  # noqa: C901
        """Returns a generator for all data nodes corresponding to the model
        path leaves.

        Args:
            data (Json): The data

        Yields:
            Iterator[Any]: The generator.
        """
        # Inner nodes that are blocked from being revisited. Nodes are
        # represented as (class, id) tuples. Non-identifiable classes cannot be
        # prevented from being re-visited.
        do_not_revisit: set[tuple[str, Any]] = set()
        # The stack that guides the traversal
        for path in self._paths:
            stack: list[tuple[int, Json]] = [(0, data)]
            while stack:
                depth, node = stack.pop()
                # Yield if we're at the end of the path
                if depth == len(path):
                    yield node
                    continue
                # Otherwise, add intermediate nodes to the stack unless they are None
                slot_def = path[depth]
                try:
                    next_nodes = node[slot_def.name]
                except KeyError:
                    if not slot_def.required:
                        continue
                    raise
                if not slot_def.multivalued:
                    next_nodes = [next_nodes]
                # Resolve non-inlined nodes
                if slot_def.range in self._all_classes and not slot_def.inlined:
                    next_nodes = self._resolve_non_inlined(
                        identifiers=next_nodes, class_name=slot_def.range
                    )
                # Add elements to stack
                next_range = path[depth].range
                if next_range in self._visit_once_classes:
                    for next_node in next_nodes:
                        next_hash = (
                            next_range,
                            next_node[self._get_class_identifier(next_range)],
                        )
                        if next_hash not in do_not_revisit:
                            stack.append((depth + 1, next_node))
                            do_not_revisit.add(next_hash)
                else:
                    stack.extend((depth + 1, next_node) for next_node in next_nodes)

    def _map_resources_by_id(self, submission_data: Json) -> dict[str, dict[str, Json]]:
        """Creates a mapping from class names to mappings from class identifiers
        to objects.

        Args:
            submission_data (Json): The submission data

        Returns:
            dict[str, dict[str, Json]]: The resulting mapping
        """
        resources_by_id: defaultdict[str, dict[str, Json]] = defaultdict(dict)
        for path in self._paths:
            for slot_def in path[:-1]:
                if not slot_def.inlined and slot_def.range not in resources_by_id:
                    if (
                        slot_def.range is None
                        or slot_def.range not in self._all_classes
                    ):
                        raise DataTraversalError(
                            f"Intermediate path slot '{slot_def.name}' does"
                            " not have a class range."
                        )
                    resources_by_id[slot_def.range] = get_resource_dict_of_class(
                        class_name=slot_def.range,
                        global_metadata=submission_data,
                        anchor_points_by_target=self._anchor_points,
                    )
            slot_def = path[-1]
            if (
                slot_def.range in self._all_classes
                and not slot_def.inlined
                and slot_def.range not in resources_by_id
            ):
                resources_by_id[slot_def.range] = get_resource_dict_of_class(
                    class_name=slot_def.range,
                    global_metadata=submission_data,
                    anchor_points_by_target=self._anchor_points,
                )

        return resources_by_id

    def __init__(
        self,
        *,
        model: CachedMetadataModel,
        submission_data: Json,
        origin: str,
        path_strings: list[str],
        visit_once_classes: Optional[list[str]] = None,
    ):
        """Creates a new DataSubgraph object.

        Args:
            model (MetadataModel): The LinkML metadata model
            submission_data (Json): The full submission data, a representation
            of the LinkML tree root class
            model_paths (list[ModelPath]): A list of model paths
            visit_once_classes (Optional[list[str]], optional): List of classes
            for which objects shall be traversed only once. Defaults to None.
        """
        self._model = model.model
        self._anchor_points = model.anchors_points_by_target
        self._visit_once_classes = visit_once_classes if visit_once_classes else []
        self._all_classes = list(self._model.schema_view.all_classes())
        self._paths = [
            _resolve_path(
                model=self._model,
                origin=origin,
                slot_names=path_string.split("."),
                all_classes=self._all_classes,
            )
            for path_string in path_strings
        ]
        self._resources_by_id = self._map_resources_by_id(submission_data)
        self._class_identifiers = {
            cls_name: ap.identifier_slot for cls_name, ap in self._anchor_points.items()
        }
