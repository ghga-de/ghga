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

"""Logic to check basic assumptions about the metadata model."""
from typing import Optional

from metldata.model_utils.anchors import (
    AnchorPointNotFoundError,
    InvalidAnchorPointError,
    filter_anchor_points,
    get_anchors_points_by_target,
)
from metldata.model_utils.essentials import ROOT_CLASS, MetadataModel


class MetadataModelAssumptionError(RuntimeError):
    """Raised when the assumptions about the metadata model are not met."""


def check_class_exists(model: MetadataModel, class_name: str) -> None:
    """Check that a class with the given name exists.

    Raises:
        MetadataModelAssumptionError: if validation fails.
    """
    # has a class called class_name:
    class_ = model.schema_view.get_class(class_name=class_name)

    if class_ is None:
        raise MetadataModelAssumptionError(
            f"A class called '{class_name}' is required but does not exist."
        )


def check_class_slot_exists(
    model: MetadataModel, class_name: str, slot_name: str, ignore_parents: bool = False
) -> None:
    """Check that a class with the given name exists and that it has a slot with the
    given name. If ignore_parents is set to True, slots that are inherited from parent
    classes or mixins are ignored.

    Raises:
        MetadataModelAssumptionError: if validation fails.
    """
    check_class_exists(model=model, class_name=class_name)

    all_slots = model.schema_view.class_slots(
        class_name=class_name, direct=ignore_parents
    )

    if slot_name not in all_slots:
        raise MetadataModelAssumptionError(
            f"A slot called '{slot_name}' is required but does not exist"
            + f" in the '{class_name}' class."
            " Inherited slots are ignored."
            if ignore_parents
            else f"A slot called '{slot_name}' is required but does not exist"
            + f" in the '{class_name}' class or its parents classes and mixins."
        )


def check_root_class_existence(model: MetadataModel) -> None:
    """Check the existence of a root class that is called as defined in ROOT_CLASS.

    Raises:
        MetadataModelAssumptionError: if validation fails.
    """
    # has a tree root called ROOT_CLASS:
    root_class = model.schema_view.get_class(class_name=ROOT_CLASS)

    if root_class is None:
        raise MetadataModelAssumptionError(
            f"A {ROOT_CLASS} class is required but does not exist."
        )
    if not root_class.tree_root:
        raise MetadataModelAssumptionError(
            f"The {ROOT_CLASS} class must have the tree_root property set to true."
        )


def check_anchor_points(
    model: MetadataModel, classes: Optional[list[str]] = None
) -> None:
    """Checks the anchor points of the root class. If classes is specified, also checks
    that anchor points for the classes exist.

    Raises:
        MetadataModelAssumptionError: if validation fails.
    """
    try:
        anchor_points_by_target = get_anchors_points_by_target(model=model)
    except InvalidAnchorPointError as error:
        raise MetadataModelAssumptionError(
            f"The model has invalid anchor points: {error}"
        ) from error

    if classes is not None:
        try:
            _ = filter_anchor_points(
                anchor_points_by_target=anchor_points_by_target,
                classes_of_interest=set(classes),
            )
        except AnchorPointNotFoundError as error:
            raise MetadataModelAssumptionError(
                f"The model is missing anchor points: {error}"
            ) from error


def check_basic_model_assumption(model: MetadataModel) -> None:
    """Check that the basic assumptions that metldata makes about the metadata model
    are met. Raises a MetadataModelAssumptionError otherwise.

    Raises:
        MetadataModelAssumptionError: if validation fails.
    """
    check_root_class_existence(model=model)
    check_anchor_points(model=model)
