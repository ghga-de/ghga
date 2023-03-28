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

"""test the manipulate module"""

from linkml_runtime.linkml_model.meta import SlotDefinition

from metldata.model_utils.manipulate import add_slot_if_not_exists, upsert_class_slot
from tests.fixtures.metadata_models import MINIMAL_VALID_METADATA_MODEL


def test_add_slot_if_not_exists_exists():
    """Test add_slot_if_not_exists if the slot exists."""

    # try to change existing has_file slot to string:
    new_slot = SlotDefinition(name="has_file", range="string")

    original_model = MINIMAL_VALID_METADATA_MODEL
    original_schema_view = original_model.schema_view

    updated_schema_view = add_slot_if_not_exists(
        schema_view=original_schema_view, new_slot=new_slot
    )
    updated_model = updated_schema_view.export_model()

    # nothing should have changed:
    assert updated_model == original_model


def test_add_slot_if_not_exists_not_exists():
    """Test add_slot_if_not_exists if the slot does not exist."""

    new_slot = SlotDefinition(name="test", range="string")

    original_model = MINIMAL_VALID_METADATA_MODEL
    original_schema_view = original_model.schema_view

    updated_schema_view = add_slot_if_not_exists(
        schema_view=original_schema_view, new_slot=new_slot
    )

    # make sure that the updated model differs from the original in the new slot:
    original_model_slots = set(original_schema_view.all_slots())
    updated_model_slots = set(updated_schema_view.all_slots())
    assert updated_model_slots.difference(original_model_slots) == {new_slot.name}


def test_upsert_class_slot_exists():
    """Test upsert_class_slot if the slot exists."""

    # change existing has_file slot to string in the Dataset class:
    class_name = "Dataset"
    new_slot = SlotDefinition(name="has_file", range="string")

    original_model = MINIMAL_VALID_METADATA_MODEL
    original_schema_view = original_model.schema_view

    updated_schema_view = upsert_class_slot(
        schema_view=original_schema_view, class_name=class_name, new_slot=new_slot
    )

    # induced_slot should have changed:
    updated_class_slot = updated_schema_view.induced_slot(
        slot_name=new_slot.name, class_name=class_name
    )
    assert updated_class_slot.range == "string"

    # check that the global slot definition has_not changed:
    updated_global_slot = updated_schema_view.get_slot(slot_name=new_slot.name)
    assert updated_global_slot.range == "File"


def test_upsert_class_slot_not_exists():
    """Test upsert_class_slot if the slot does not exists."""

    class_name = "Dataset"
    new_slot = SlotDefinition(name="test", range="string")

    original_model = MINIMAL_VALID_METADATA_MODEL
    original_schema_view = original_model.schema_view

    updated_schema_view = upsert_class_slot(
        schema_view=original_schema_view, class_name=class_name, new_slot=new_slot
    )

    # check that the slot exists on the global and class level in an identical fashion:
    updated_class_slot = updated_schema_view.induced_slot(
        slot_name=new_slot.name, class_name=class_name
    )
    updated_global_slot = updated_schema_view.get_slot(slot_name=new_slot.name)
    assert updated_class_slot.range == updated_global_slot.range == new_slot.range
