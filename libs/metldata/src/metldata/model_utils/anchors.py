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

"""All classes that shall be referenced by ID must be linked in the root class of the
model. The slot in the root that links to a specific class is called the anchor point of
that class. This module provides logic for handling these anchor points.
"""

from linkml_runtime import SchemaView
from linkml_runtime.linkml_model import SlotDefinition
from pydantic import BaseModel, ConfigDict, Field

from metldata.model_utils.essentials import ROOT_CLASS, MetadataModel
from metldata.model_utils.identifiers import get_class_identifiers


class InvalidAnchorPointError(RuntimeError):
    """Raised when an anchor point defined in a model is invalid."""


class AnchorPointNotFoundError(RuntimeError):
    """Raised when no anchor point was found for a specific class."""


class ClassNotAnchoredError(RuntimeError):
    """Raised when a class is not anchored."""


class AnchorPoint(BaseModel):
    """A model for describing an anchor point for the specified target class."""

    model_config = ConfigDict(frozen=True)

    target_class: str = Field(..., description="The name of the class to be targeted.")
    identifier_slot: str = Field(
        ...,
        description=(
            "The name of the slot in the target class that is used as identifier."
        ),
    )
    root_slot: str = Field(
        ...,
        description=(
            "The name of the slot in the root class used to link to the target class."
        ),
    )


def check_root_slot(slot: SlotDefinition):
    """Make sure that the given root slot is a valid anchor point. Validates that the
    slot is multivalued, required, and inlined but not inlined as list.

    Raises:
        InvalidAnchorPointError: if validation fails.
    """
    if not slot.multivalued:
        raise InvalidAnchorPointError(
            f"The anchor point at the slot '{slot.name}' is not multivalued."
        )

    if slot.inlined is None:
        raise InvalidAnchorPointError(
            f"The inlined attribute for slot '{slot.name}' is not defined."
        )

    if not slot.inlined:
        raise InvalidAnchorPointError(
            f"The inlined attribute for slot '{slot.name}' is set to False,"
            + " however, slots in the root class must be inlined."
        )

    if not slot.inlined_as_list:
        raise InvalidAnchorPointError(
            f"The inlined_as_list attribute for slot '{slot.name}' is set to False,"
            + " however, slots in the root class must be inlined as list."
        )

    if not slot.required:
        raise InvalidAnchorPointError(
            f"The anchor point at the slot '{slot.name}' is not required."
        )


def get_slot_target_class(*, slot: SlotDefinition, schema_view: SchemaView) -> str:
    """Checks that the specified slot refers to another class and returns the name
    of that class.
    """
    if slot.range is None:
        raise InvalidAnchorPointError(
            f"The slot '{slot.name}', which is used as anchor point, has no range"
            + " defined."
        )

    target_class = schema_view.get_class(class_name=slot.range)

    if target_class is None:
        raise InvalidAnchorPointError(
            f"The range of slot '{slot.name}', which is used as anchor point, does not"
            + " point to a valid class."
        )

    return slot.range


def get_anchor_points(*, model: MetadataModel) -> set[AnchorPoint]:
    """Get all anchor points of the specified model."""
    identifiers_by_class = get_class_identifiers(model=model)

    schema_view = model.schema_view
    root_slots = schema_view.class_induced_slots(class_name=ROOT_CLASS)

    # validation root slots:
    for root_slot in root_slots:
        check_root_slot(root_slot)

    anchor_point: set[AnchorPoint] = set()
    for root_slot in root_slots:
        target_class = get_slot_target_class(slot=root_slot, schema_view=schema_view)
        identifier = identifiers_by_class[target_class]
        if not identifier:
            raise InvalidAnchorPointError(
                f"The class '{target_class}' has no identifier defined."
            )

        anchor_point.add(
            AnchorPoint(
                target_class=target_class,
                identifier_slot=identifier,
                root_slot=str(root_slot.name),
            )
        )

    return anchor_point


def get_anchors_points_by_target(*, model: MetadataModel) -> dict[str, AnchorPoint]:
    """Get a dictionary with the keys corresponding to class names and the values
    corresponding to anchor points.
    """
    anchor_points = get_anchor_points(model=model)

    return {anchor_point.target_class: anchor_point for anchor_point in anchor_points}


def filter_anchor_points(
    *, anchor_points_by_target: dict[str, AnchorPoint], classes_of_interest: set[str]
) -> dict[str, AnchorPoint]:
    """Filter the provided anchor points by a list of classes of interest.

    Raises:
        AnchorPointNotFoundError: if no anchor point was found for a class of interest.
    """
    # check if anchor points exists for all classes:
    classes_without_anchor_points = classes_of_interest.difference(
        anchor_points_by_target.keys()
    )
    if classes_without_anchor_points:
        raise AnchorPointNotFoundError(
            "Following classes have no anchor points: "
            + ", ".join(sorted(classes_without_anchor_points))
        )

    return {
        class_name: anchor_point
        for class_name, anchor_point in anchor_points_by_target.items()
        if class_name in classes_of_interest
    }


def lookup_anchor_point(
    *, class_name: str, anchor_points_by_target: dict[str, AnchorPoint]
) -> AnchorPoint:
    """Lookup the anchor point for the given class."""
    anchor_point = anchor_points_by_target.get(class_name)

    if anchor_point is None:
        raise AnchorPointNotFoundError(
            f"Cannot find anchor point class '{class_name}'."
        )

    return anchor_point


def invert_anchor_points_by_target(
    anchor_points_by_target: dict[str, AnchorPoint],
) -> dict[str, str]:
    """Convert the anchor points by target dict into an class by anchor point dict."""
    return {
        anchor_point.root_slot: class_name
        for class_name, anchor_point in anchor_points_by_target.items()
    }


def get_target_by_anchor_point(*, model: MetadataModel) -> dict[str, str]:
    """Get a mapping from the root slot where a class is anchored to the corresponding
    class.
    """
    anchor_points = get_anchor_points(model=model)

    return {
        anchor_point.root_slot: anchor_point.target_class
        for anchor_point in anchor_points
    }


def lookup_class_by_anchor_point(
    *, root_slot: str, target_by_anchor_point: dict[str, str]
) -> str:
    """Lookup the class for the given anchor point."""
    class_name = target_by_anchor_point.get(root_slot)

    if class_name is None:
        raise ClassNotAnchoredError(
            f"Cannot find class for anchor point with root slot '{root_slot}'."
        )

    return class_name
