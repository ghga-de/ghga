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

"""A transformation that normalizes a model to a canonical form."""

from linkml_runtime import SchemaView
from linkml_runtime.linkml_model.meta import SlotDefinition

from metldata.model_utils.essentials import MetadataModel


def resolve_inheritance(output_model: dict, input_schema_view: SchemaView) -> None:
    """Resolve inheritance by embedding all slots into the derived classes."""
    all_slot_names = set()
    for cls_name, cls in output_model["classes"].items():
        slot_usages = input_schema_view.class_induced_slots(cls_name)
        slot_names = [slot.name for slot in slot_usages]
        # Integrate all slot information
        cls["slot_usage"] = {slot_def.name: slot_def for slot_def in slot_usages}
        cls["slots"] = slot_names
        # Update all_slot names for globally reduced set of actually used slot
        # names.
        all_slot_names.update(slot_names)
        # Remove inheritance
        cls["is_a"] = None
        cls["mixins"] = []
        cls["attributes"] = []
    # Rewrite slots
    output_model["slots"] = {
        slot_name: SlotDefinition(name=slot_name) for slot_name in all_slot_names
    }


def embed_types(output_model: dict, input_schema_view: SchemaView) -> None:
    """Embed types from the types schema into the model."""
    if "linkml:types" in output_model["imports"]:
        # Load the types schema
        types_schema = input_schema_view.load_import("linkml:types")
        # Embed types
        if not isinstance(types_schema.types, dict):
            raise RuntimeError("Types schema does not contain a dict of types.")
        for type_name, type_def in types_schema.types.items():
            if type_name not in output_model["types"]:
                output_model["types"][type_name] = type_def
        # Embed prefixes
        if not isinstance(types_schema.prefixes, dict):
            raise RuntimeError("Types schema does not contain a dict of types.")
        for prefix_name, prefix_def in types_schema.prefixes.items():
            if prefix_name not in output_model["prefixes"]:
                output_model["prefixes"][prefix_name] = prefix_def
        # Drop import
        output_model["imports"].remove("linkml:types")


def normalize_model(model: MetadataModel) -> MetadataModel:
    """Normalize model to canonical form with all slots being globally defined
    only as empty stubs and all slot definitions being defined in the slot_usage
    of the respective class.
    """
    output_model = model.as_dict()
    schema_view = model.schema_view

    resolve_inheritance(output_model, schema_view)
    embed_types(output_model, schema_view)

    return MetadataModel(**output_model)
