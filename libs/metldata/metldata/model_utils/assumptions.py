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
from metldata.model_utils.anchors import InvalidAnchorPointError, get_anchor_points
from metldata.model_utils.essentials import ROOT_CLASS, MetadataModel


class MetadataModelAssumptionError(RuntimeError):
    """Raised when the assumptions about the metadata model are not met."""


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


def check_anchor_points(model: MetadataModel) -> None:
    """Checks the anchor points of the root class.

    Raises:
        MetadataModelAssumptionError: if validation fails.
    """

    try:
        _ = get_anchor_points(model=model)
    except InvalidAnchorPointError as error:
        raise MetadataModelAssumptionError(
            f"The model has invalid anchor points: {error}"
        ) from error


def check_basic_model_assumption(model: MetadataModel) -> None:
    """Check that the basic assumptions that metldata makes about the metadata model
    are met. Raises a MetadataModelAssumptionError otherwise.

    Raises:
        MetadataModelAssumptionError: if validation fails.
    """

    check_root_class_existence(model=model)
    check_anchor_points(model=model)
