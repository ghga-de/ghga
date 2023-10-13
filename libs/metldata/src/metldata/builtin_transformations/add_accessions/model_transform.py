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

"""Logic for transforming metadata models."""


from copy import deepcopy
from typing import Optional, cast

from linkml_runtime.linkml_model.meta import ClassDefinition, SlotDefinition

from metldata.model_utils.anchors import get_anchors_points_by_target
from metldata.model_utils.essentials import ExportableSchemaView, MetadataModel
from metldata.model_utils.identifiers import get_class_identifiers
from metldata.model_utils.manipulate import upsert_class
from metldata.transform.base import MetadataModelTransformationError


def unset_identifier(
    *, class_definition: ClassDefinition, class_identifiers: dict[str, Optional[str]]
) -> ClassDefinition:
    """Get a modified copy of the provided class definition with the identifier being
    unset.
    """
    identifier_slot_name = class_identifiers[class_definition.name]
    if identifier_slot_name is None:
        raise RuntimeError(  # This should never happen
            f"Class {class_definition.name} does not have an identifier."
        )

    modified_class = deepcopy(class_definition)

    if not modified_class.slot_usage:
        modified_class.slot_usage = {}
    elif not isinstance(modified_class.slot_usage, dict):
        raise RuntimeError(  # This should never happen
            f"Class {class_definition.name} has a slot_usage that is not a dict."
        )

    identifier_slot = modified_class.slot_usage.get(
        identifier_slot_name,
        SlotDefinition(name=identifier_slot_name),
    )
    identifier_slot = cast(SlotDefinition, identifier_slot)
    identifier_slot.identifier = False

    modified_class.slot_usage[identifier_slot_name] = identifier_slot

    return modified_class


def get_accession_slot(*, accession_slot_name: str) -> SlotDefinition:
    """Generate a slot definition for the accession slot."""
    return SlotDefinition(
        name=accession_slot_name,
        identifier=True,
        required=True,
    )


def add_accessions_to_class(
    *,
    class_definition: ClassDefinition,
    accession_slot_name: str,
    class_identifiers: dict[str, Optional[str]],
) -> ClassDefinition:
    """Get a modified copy of the provided class definition with the accession slot
    being added as identifier.
    """
    modified_class = unset_identifier(
        class_definition=class_definition, class_identifiers=class_identifiers
    )

    if not isinstance(modified_class.slots, list):
        raise RuntimeError(  # This should never happen
            f"Class {class_definition.name} has a slots that is not a list."
        )
    modified_class.slots.append(accession_slot_name)

    modified_class.slot_usage[accession_slot_name] = get_accession_slot(
        accession_slot_name=accession_slot_name
    )

    return modified_class


def add_global_accession_slot(
    *,
    schema_view: ExportableSchemaView,
    accession_slot_name: str,
    accession_slot_description: str,
) -> ExportableSchemaView:
    """Get a modified copy of the provided schema view with the accession slot being
    added to the global scope.
    """
    if schema_view.get_slot(slot_name=accession_slot_name):
        raise MetadataModelTransformationError(
            f"The slot name '{accession_slot_name}' cannot be used as accession, it is"
            + " already in use."
        )

    accession_slot = SlotDefinition(
        name=accession_slot_name, description=accession_slot_description
    )

    modified_schema_view = deepcopy(schema_view)
    modified_schema_view.add_slot(slot=accession_slot)

    return modified_schema_view


def add_accessions_to_model(
    *, model: MetadataModel, accession_slot_name: str, accession_slot_description: str
) -> MetadataModel:
    """Get a modified copy of the provided model with the accession slot being added as
    identifier.
    """
    anchor_points_by_target = get_anchors_points_by_target(model=model)
    class_identifiers = {
        class_name: identifier
        for class_name, identifier in get_class_identifiers(model=model).items()
        if class_name in anchor_points_by_target
    }
    schema_view = model.schema_view

    modified_schema_view = add_global_accession_slot(
        schema_view=schema_view,
        accession_slot_name=accession_slot_name,
        accession_slot_description=accession_slot_description,
    )

    for class_name in class_identifiers:
        class_definition = modified_schema_view.get_class(class_name=class_name)
        if not class_definition:
            raise RuntimeError(  # This should never happen
                f"Class with name '{class_name}' does not exist."
            )

        class_definition = add_accessions_to_class(
            class_definition=class_definition,
            accession_slot_name=accession_slot_name,
            class_identifiers=class_identifiers,
        )
        modified_schema_view = upsert_class(
            schema_view=modified_schema_view, class_definition=class_definition
        )

    return modified_schema_view.export_model()
