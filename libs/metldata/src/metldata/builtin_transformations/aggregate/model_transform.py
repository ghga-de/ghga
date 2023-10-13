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

import itertools
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict
from typing import Optional

from linkml_runtime.linkml_model import ClassDefinition, SlotDefinition
from stringcase import snakecase

from metldata.builtin_transformations.aggregate.config import (
    AggregateConfig,
    Aggregation,
)
from metldata.builtin_transformations.aggregate.models import (
    MinimalClass,
    MinimalLinkMLModel,
    MinimalNamedSlot,
    MinimalSlot,
)
from metldata.model_utils.anchors import AnchorPoint
from metldata.model_utils.essentials import ROOT_CLASS, MetadataModel
from metldata.model_utils.identifiers import get_class_identifier
from metldata.model_utils.manipulate import add_anchor_point, upsert_class_slot
from metldata.transform.base import MetadataModelTransformationError

Path = tuple[Optional[str], ...]


class PathMatrix:
    """Represents a matrix of data paths."""

    __paths: list[Path]
    leaf_slots: list[MinimalNamedSlot]

    def path_leaves(self) -> Iterable[str]:
        """Yields the path leaves of all paths"""
        for path in self.__paths:
            for node in reversed(path):
                if node is not None:
                    yield node
                    break

    def validate_paths(self) -> None:
        """Validates that the specified output paths are compatible, i.e. that
        no path is a prefix of another path. Note that this implicitly includes
        checking for identical paths.

        Raises:
        MetadataModelTransformationError: If one path is a prefix of another.
        """
        for path_a, path_b in itertools.combinations(self.__paths, r=2):
            min_len = min(len(path_a), len(path_b))
            if path_a[:min_len] == path_b[:min_len]:
                raise MetadataModelTransformationError(
                    "Incompatible output paths:"
                    f" '{'.'.join(str(elem) for elem in path_a)}"
                    f" and {'.'.join(str(elem) for elem in path_b)}."
                )

    def load_leaf_slots(self, leaf_slots: list[MinimalSlot]) -> None:
        """Combines the paths and the specified leaf slots to NamedSlots and
        stores them.
        """
        self.leaf_slots = [
            MinimalNamedSlot(slot_name=slot_name, **asdict(slot))
            for slot_name, slot in zip(self.path_leaves(), leaf_slots)
        ]

    @property
    def paths(self):
        """Returns a copy of the paths."""
        return self.__paths[:]

    @property
    def max_depth(self):
        """The maximum depth among all paths"""
        # All path lengths are equal after normalization
        return len(self.__paths[0]) if self.__paths else 0

    def normalize_path_matrix(self) -> None:
        """Equalize the lengths of all paths by appending None values to paths
        shorter than then maximum path length.
        """
        max_depth = max(len(path) for path in self.__paths)
        self.__paths = [
            path + (None,) * (max_depth - len(path)) for path in self.__paths
        ]

    def add_path(self, path: Path, leaf_slot: MinimalNamedSlot) -> None:
        """Add a path"""
        for existing_path in self.__paths:
            if path == existing_path[: len(path)]:
                raise MetadataModelTransformationError(
                    f"Cannot add conflicting path {path}."
                )
        self.__paths.append(path)
        self.leaf_slots.append(leaf_slot)
        self.normalize_path_matrix()

    def load_path_strings(self, paths: list[list[str]]) -> None:
        """Given a list of lists, appends None values to each list until the
        length of the longest list is matched.
        """
        self.__paths = list(map(Path, paths))
        self.validate_paths()
        self.normalize_path_matrix()

    def compact_path_matrix(self) -> None:
        """Eliminate trailing None columns in the path matrix."""
        while self.__paths and all(path[-1] is None for path in self.__paths):
            self.__paths = [path[:-1] for path in self.__paths]

    def delete_path(self, path: Path) -> None:
        """Deletes the specified path from the path matrix and leaf_slots"""
        idx = self.__paths.index(path)
        del self.__paths[idx]
        del self.leaf_slots[idx]
        self.compact_path_matrix()

    def __init__(self, path_strings: list[str], leaf_slots: list[MinimalSlot]):
        """Creates a new ModelGenerator"""
        paths = [path_string.split(".") for path_string in path_strings]
        self.load_path_strings(paths)
        self.load_leaf_slots(leaf_slots)


def update_metadata_model(model: MetadataModel, min_model: MinimalLinkMLModel) -> None:
    """Update a MetadataModel based on the provided minimal class representations.

    Bare bone slots will be added based on all slot names that are found in the
    provided classes. One class will be created according to each provided class
    with the slots being configured in slot_usage entirely.

    Args:
        model (MetadataModel): The MetadataModel to modify in place.
        class_names (dict[MinimalClass, str]): A dictionary of MinimalClasses
        with associated class names.
    """
    # Enumerate all unique slot names and add the slots to the model
    all_min_classes = itertools.chain(
        min_model.anonymous_classes, min_model.named_classes.values()
    )
    slot_names = sorted({slot.slot_name for cls in all_min_classes for slot in cls})

    for slot_name in slot_names:
        model.schema_view.add_slot(slot=SlotDefinition(name=slot_name))
    new_class_defs: dict[str, ClassDefinition] = {}

    for cls_name, min_cls_def in min_model.all_classes():
        new_class_defs[cls_name] = ClassDefinition(
            name=cls_name,
            slots=sorted(slot.slot_name for slot in min_cls_def),
            slot_usage={
                slot.slot_name: {
                    "range": slot.range,
                    "multivalued": slot.multivalued,
                }
                for slot in sorted(min_cls_def)
            },
        )

    all_classes = model.schema_view.all_classes()
    for cls_name, cls_def in new_class_defs.items():  # noqa: B007
        for slot_name, slot_config in cls_def.slot_usage.items():  # noqa: B007
            slot_range = slot_config["range"]
            if slot_range in all_classes or slot_range in new_class_defs:
                slot_config["inlined"] = True
                if slot_config["multivalued"]:
                    slot_config["inlined_as_list"] = True

    for cls_def in new_class_defs.values():
        model.schema_view.add_class(cls_def)


def add_aggregation(min_model: MinimalLinkMLModel, aggregation: Aggregation) -> None:
    """Adds the required slots and classes defined by the provided aggregation
    to the provided minimal model.
    """
    root_name = aggregation.output
    path_strings = [operation.output_path for operation in aggregation.operations]
    leaf_ranges = [op.function.result_range_name for op in aggregation.operations]
    leaf_multivalued = [op.function.result_multivalued for op in aggregation.operations]

    path_matrix = PathMatrix(
        path_strings=path_strings,
        leaf_slots=[
            MinimalSlot(range=slot_range, multivalued=mv)
            for slot_range, mv in zip(leaf_ranges, leaf_multivalued)
        ],
    )

    for _ in range(path_matrix.max_depth):
        classes: dict[Path, set[MinimalNamedSlot]] = defaultdict(set[MinimalNamedSlot])
        for idx, path_prefix in enumerate(path_matrix.paths):
            if path_prefix[-1]:
                classes[path_prefix[:-1]].add(path_matrix.leaf_slots[idx])
        for path_prefix, cls_set in classes.items():
            # Delete all paths with this prefix
            for slot in cls_set:
                path_matrix.delete_path(path_prefix + (slot.slot_name,))  # noqa: RUF005
            # Construct a class for this prefix and check if a matching
            # class already exists.
            cls = MinimalClass(cls_set)

            if not path_prefix:
                # We have reached the root of the output path model
                min_model.add_named_class(cls_def=cls, cls_name=root_name)
                slot_range = root_name
            else:  # noqa: PLR5501
                # We are at an intermediate model and will use generic class
                # names and potentially re-use the classes as they fit
                if cls in min_model.anonymous_classes:
                    slot_range = min_model.anonymous_classes[cls]
                else:
                    slot_range = min_model.add_anonymous_class(cls)
            # Add the prefix as a new path with the identified class as range
            if path_prefix and path_prefix[-1]:
                path_matrix.add_path(
                    path_prefix,
                    MinimalNamedSlot(
                        slot_name=path_prefix[-1],
                        multivalued=False,
                        range=slot_range,
                    ),
                )


def bare_bone_model_from_other(model: MetadataModel) -> MetadataModel:
    """Create a new MetadataModel with no classes, enums, slots and subsets. All
    other SchemaDefinition attributes are kept.
    """
    model_dict = model.as_dict(essential=False)
    del model_dict["enums"]
    del model_dict["slots"]
    del model_dict["subsets"]
    model_dict["classes"] = {
        ROOT_CLASS: ClassDefinition(name=ROOT_CLASS, tree_root=True)
    }
    return MetadataModel(**model_dict)


def get_identifier_slot_names(
    input_model: MetadataModel, origin_map: dict[str, str]
) -> dict[str, str]:
    """Associate the correct identifier slot name with every output class.

    Args:
        input_model (MetadataModel): The input original metadata model
        origin_map (dict[str,str]): A dictionary mapping input class names to output class names

    Returns:
        dict[str,str]: A dictionary mapping output class names to identifier slot names
    """
    id_slot_map: dict[str, str] = {}
    for in_cls_name, out_cls_name in origin_map.items():
        slot_name = get_class_identifier(input_model, in_cls_name)
        if not slot_name:
            raise MetadataModelTransformationError(
                f"No identifier slot for class {in_cls_name}."
            )
        id_slot_map[out_cls_name] = slot_name
    return id_slot_map


def add_identifier_slots(
    input_model: MetadataModel,
    output_model: MetadataModel,
    origin_map: dict[str, str],
    id_slot_map: dict[str, str],
) -> MetadataModel:
    """Adds identifier slots to the high level output model classes. The slot
    name and range is inferred from the original input classes.

    Args:
        input_model (MetadataModel): _description_
        output_model (MetadataModel): _description_
        class_map (list[tuple[str, str]]): _description_

    Raises:
        MetadataModelTransformationError: _description_

    Returns:
        MetadataModel: _description_
    """
    output_schema_view = output_model.schema_view
    for in_class_name, out_class_name in origin_map.items():
        slot_name = id_slot_map[out_class_name]
        input_slot = input_model.schema_view.induced_slot(slot_name, in_class_name)
        output_schema_view = upsert_class_slot(
            schema_view=output_schema_view,
            class_name=out_class_name,
            new_slot=SlotDefinition(
                name=slot_name, range=input_slot.range, identifier=True
            ),
        )

    return output_schema_view.export_model()


def build_aggregation_model(
    model: MetadataModel, config: AggregateConfig
) -> MetadataModel:
    """Create a data model for the result of an aggregation transformation as
    described in an AggregateConfig

    Args:
        model (MetadataModel): The LinkML model to transform
        config (AggregateConfig): The config

    Returns:
        MetadataModel: A new, modified MetadataModel
    """
    # Reduce model to a bare bone model

    min_output_model = MinimalLinkMLModel()

    # Add function output classes
    for agg_func in (
        op.function for agg in config.aggregations for op in agg.operations
    ):
        cls_def = agg_func.result_range_cls_def
        cls_name = agg_func.result_range_name
        if cls_def:
            min_output_model.add_named_class(cls_def=cls_def, cls_name=cls_name)

    # Add upstream classes
    for aggregation in config.aggregations:
        add_aggregation(min_model=min_output_model, aggregation=aggregation)

    output_model = bare_bone_model_from_other(model)
    # Add slots and classes to the bare bone metadata model
    update_metadata_model(output_model, min_output_model)

    # Add identifier slots to classes
    origin_map = {agg.input: agg.output for agg in config.aggregations}
    id_slot_map = get_identifier_slot_names(input_model=model, origin_map=origin_map)
    output_model = add_identifier_slots(
        input_model=model,
        output_model=output_model,
        origin_map=origin_map,
        id_slot_map=id_slot_map,
    )

    # Anchor the output classes
    schema_view = output_model.schema_view
    for aggregation in config.aggregations:
        root_slot = snakecase(aggregation.output)
        root_slot = root_slot + "s" if not root_slot.endswith("s") else root_slot
        schema_view = add_anchor_point(
            schema_view=schema_view,
            anchor_point=AnchorPoint(
                target_class=aggregation.output,
                identifier_slot=id_slot_map[aggregation.output],
                root_slot=root_slot,
            ),
        )

    return schema_view.export_model()
