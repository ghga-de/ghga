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

"""Utils for LinkML schema"""

from typing import Optional

from linkml.utils.datautils import infer_root_class
from linkml_runtime.utils.schemaview import SchemaView, SlotDefinition


def get_range_class(schema_view, slot_def: SlotDefinition) -> Optional[str]:
    """Return the range class for a slot

    Args:
        slot_def (SlotDefinition): Slot Definition

    Returns:
        Optional[str]: Range class for a slot
    """
    return slot_def.range if slot_def.range in schema_view.all_classes() else None


def get_target_class(schema: str) -> Optional[str]:
    """
    Infer the root class from schema
    Args:
        schema (str): YAML schema as the string

    Returns:
        class name for root class, if found in the scheme
    """
    with open(schema, encoding="utf8") as file:
        input_schema = file.read()
        return infer_root_class(SchemaView(input_schema))
