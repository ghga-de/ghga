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

"""Handling identifiers of classes in a metadata model."""

from typing import Optional

from metldata.model_utils.essentials import ROOT_CLASS, MetadataModel


def get_class_identifier(model: MetadataModel, class_name: str) -> Optional[str]:
    """Get the identifier of a class in a metadata model.

    Returns:
        The identifier of the class, or None if the class does not have an identifier.
    """
    schema_view = model.schema_view

    for slot_name in schema_view.class_slots(class_name=class_name):
        slot_def = schema_view.induced_slot(slot_name=slot_name, class_name=class_name)
        if slot_def.identifier:
            return str(slot_def.name)

    return None


def get_class_identifiers(model: MetadataModel) -> dict[str, Optional[str]]:
    """Get the identifiers of all classes in a metadata model.

    Returns:
        A dictionary with the class names as keys and the identifiers as values. If a
        class does not have an identifier, the value is None.
    """
    schema_view = model.schema_view

    identifiers_by_class: dict[str, Optional[str]] = {}
    for class_name in schema_view.all_classes():
        if class_name == ROOT_CLASS:
            continue  # Root class does not have an identifier
        class_def = schema_view.get_class(class_name=class_name)
        if class_def.mixin or class_def.abstract:
            continue  # Mixins and abstract classes do not have an identifier
        identifier = get_class_identifier(model=model, class_name=class_name)
        identifiers_by_class[class_name] = identifier

    return identifiers_by_class
