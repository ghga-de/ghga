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

from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from itertools import combinations
from typing import Iterable, Optional, cast

from linkml_runtime.linkml_model import ClassDefinition, SlotDefinition

from metldata.builtin_transformations.aggregate.config import AggregateConfig
from metldata.builtin_transformations.aggregate.models import (
    MinimalClass,
    MinimalNamedSlot,
    MinimalSlot,
)
from metldata.model_utils.essentials import MetadataModel
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
            MetadataModelTransformationError: If one path is a prefix of another."""
        for path_a, path_b in combinations(self.__paths, r=2):
            min_len = min(len(path_a), len(path_b))
            if path_a[:min_len] == path_b[:min_len]:
                raise MetadataModelTransformationError(
                    "Incompatible output paths:"
                    f" '{'.'.join(str(elem) for elem in path_a)}"
                    f" and {'.'.join(str(elem) for elem in path_b)}."
                )

    def load_leaf_slots(self, leaf_slots: list[MinimalSlot]) -> None:
        """Combines the paths and the specified leaf slots to NamedSlots and
        stores them."""
        self.leaf_slots = [
            MinimalNamedSlot(slot_name=slot_name, **asdict(slot))
            for slot_name, slot in zip(self.path_leaves(), leaf_slots)
        ]

    @property
    def paths(self):
        """Returns a copy of the paths."""
        return deepcopy(self.__paths)

    @property
    def max_depth(self):
        """The maximum depth among all paths"""
        return len(self.__paths[0]) if self.__paths else 0

    def normalize_path_matrix(self) -> None:
        """Equalize the lengths of all paths by appending None values to paths
        shorter than then maximum path length."""
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
        length of the longest list is matched."""
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


def update_metadata_model(
    model: MetadataModel, class_names: dict[MinimalClass, str]
) -> None:
    """Update a MetadataModel based on the provided minimal class representations.

    Bare bone slots will be added based on all slot names that are found in the
    provided classes. One class will be created according to each provided class
    with the slots being configured in slot_usage entirely.

    Args:
        model (MetadataModel): The MetadataModel to modify in place.
        class_names (dict[MinimalClass, str]): A dictionary of MinimalClasses
        with associated class names.
    """
    slot_names = {slot.slot_name for cls in class_names for slot in cls}
    for slot_name in slot_names:
        model.schema_view.add_slot(slot=SlotDefinition(name=slot_name))
    new_class_defs: dict[str, ClassDefinition] = {}

    for cls, cls_name in class_names.items():
        new_class_defs[cls_name] = ClassDefinition(
            name=cls_name,
            slots=[slot.slot_name for slot in cls],
            tree_root=cls_name == "Root",
            slot_usage={
                slot.slot_name: {
                    "range": slot.range,
                    "multivalued": slot.multivalued,
                }
                for slot in cls
            },
        )
    all_classes = model.schema_view.all_classes()
    for cls_name, cls_def in new_class_defs.items():
        for slot_name, slot_config in cast(dict[str, dict], cls_def.slot_usage).items():
            slot_range = slot_config["range"]
            if slot_range in all_classes or slot_range in new_class_defs:
                slot_config["inlined"] = True
                if slot_config["multivalued"]:
                    slot_config["inlined_as_list"] = True

    for cls_def in new_class_defs.values():
        model.schema_view.add_class(cls_def)


def build_classes(
    path_strings: list[str], leaf_ranges: list[str], leaf_multivalued: list[bool]
) -> dict[MinimalClass, str]:
    """Build the LinkML Model"""
    path_matrix = PathMatrix(
        path_strings=path_strings,
        leaf_slots=[
            MinimalSlot(range=slot_range, multivalued=mv)
            for slot_range, mv in zip(leaf_ranges, leaf_multivalued)
        ],
    )

    class_names: dict[MinimalClass, str] = {}
    for _ in reversed(range(0, path_matrix.max_depth)):
        classes: dict[Path, set[MinimalNamedSlot]] = defaultdict(set[MinimalNamedSlot])
        for idx, path_prefix in enumerate(path_matrix.paths):
            if path_prefix[-1]:
                classes[path_prefix[:-1]].add(path_matrix.leaf_slots[idx])
        for path_prefix, cls_set in classes.items():
            # Delete all paths with this prefix
            for slot in cls_set:
                path_matrix.delete_path(path_prefix + (slot.slot_name,))
            # Construct a class for this prefix and check if a matching
            # class already exists.
            cls = MinimalClass(cls_set)
            if cls in class_names:
                slot_range = class_names[cls]
            else:
                slot_range = f"Class{len(class_names)}" if path_prefix else "Root"
                class_names[cls] = slot_range
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
    return class_names


def bare_bone_model_from_other(model: MetadataModel) -> MetadataModel:
    """Create a new MetadataModel with no classes, enums, slots and subsets. All
    other SchemaDefinition attributes are kept."""
    model_dict = model.as_dict(essential=False)
    del model_dict["classes"]
    del model_dict["enums"]
    del model_dict["slots"]
    del model_dict["subsets"]
    return MetadataModel(**model_dict)


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
    new_model = bare_bone_model_from_other(model)

    # Generate the LinkML classes for the inner data graph nodes
    transformations = [agg.operation for agg in config.aggregations]
    intermediate_classes = build_classes(
        path_strings=[agg.output_path for agg in config.aggregations],
        leaf_ranges=[Trans.result_range()[0] for Trans in transformations],
        leaf_multivalued=[Trans.result_multivalued() for Trans in transformations],
    )

    # Extract the LinkML classes for the leaf nodes from the config
    output_classes = cast(
        dict[MinimalClass, str],
        {
            Trans.result_range()[1]: Trans.result_range()[0]
            for Trans in transformations
            if Trans.result_range()[1] is not None
        },
    )

    # Add slots and classes to the bare bone metadata model
    update_metadata_model(new_model, output_classes)
    update_metadata_model(new_model, intermediate_classes)

    return new_model
