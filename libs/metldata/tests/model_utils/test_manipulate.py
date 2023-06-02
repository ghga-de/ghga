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

import pytest
from linkml_runtime.linkml_model.meta import SlotDefinition

from metldata.model_utils.identifiers import get_class_identifier
from metldata.model_utils.manipulate import (
    ClassNotFoundError,
    ClassSlotNotFoundError,
    add_slot_if_not_exists,
    add_slot_usage_annotation,
    delete_class_slot,
    disable_identifier_slot,
    upsert_class_slot,
)
from tests.fixtures.metadata_models import VALID_MINIMAL_METADATA_MODEL


def test_add_slot_if_not_exists_exists():
    """Test add_slot_if_not_exists if the slot exists."""

    # try to change existing files slot to string:
    new_slot = SlotDefinition(name="files", range="string")

    original_model = VALID_MINIMAL_METADATA_MODEL
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

    original_model = VALID_MINIMAL_METADATA_MODEL
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

    # change existing files slot to string in the Dataset class:
    class_name = "Dataset"
    new_slot = SlotDefinition(name="files", range="string")

    original_model = VALID_MINIMAL_METADATA_MODEL
    original_schema_view = original_model.schema_view

    updated_schema_view = upsert_class_slot(
        schema_view=original_schema_view, class_name=class_name, new_slot=new_slot
    )

    # induced_slot should have changed:
    updated_class_slot = updated_schema_view.induced_slot(
        slot_name=new_slot.name, class_name=class_name
    )
    assert updated_class_slot.range == "string"

    # check that the global slot definition has not changed:
    updated_global_slot = updated_schema_view.get_slot(slot_name=new_slot.name)
    assert updated_global_slot.range == "File"


def test_upsert_class_slot_not_exists():
    """Test upsert_class_slot if the slot does not exists."""

    class_name = "Dataset"
    new_slot = SlotDefinition(name="test", range="string")

    original_model = VALID_MINIMAL_METADATA_MODEL
    original_schema_view = original_model.schema_view

    updated_schema_view = upsert_class_slot(
        schema_view=original_schema_view, class_name=class_name, new_slot=new_slot
    )

    # check that the slot exists on the global and class level in an identical fashion:
    assert new_slot.name in updated_schema_view.class_slots(class_name=class_name)
    updated_class_slot = updated_schema_view.induced_slot(
        slot_name=new_slot.name, class_name=class_name
    )
    updated_global_slot = updated_schema_view.get_slot(slot_name=new_slot.name)
    assert updated_class_slot.range == updated_global_slot.range == new_slot.range


def test_delete_class_slot_happy():
    """Test the happy path of using delete_class_slot."""

    class_name = "Dataset"
    slot_name = "files"

    original_model = VALID_MINIMAL_METADATA_MODEL
    original_schema_view = original_model.schema_view

    updated_schema_view = delete_class_slot(
        schema_view=original_schema_view, class_name=class_name, slot_name=slot_name
    )

    # check that the slot does not exist on the class level anymore:
    assert slot_name not in updated_schema_view.class_slots(class_name=class_name)

    # check that the slot still exists on the global level:
    assert updated_schema_view.get_slot(slot_name=slot_name) is not None


def test_delete_class_slot_class_not_exists():
    """Test delete_class_slot if the class does not exist."""

    class_name = "DoesNotExist"
    slot_name = "files"

    original_model = VALID_MINIMAL_METADATA_MODEL
    original_schema_view = original_model.schema_view

    with pytest.raises(ClassNotFoundError):
        delete_class_slot(
            schema_view=original_schema_view, class_name=class_name, slot_name=slot_name
        )


def test_delete_class_slot_slot_not_exists():
    """Test delete_class_slot if the slot does not exist."""

    class_name = "Dataset"
    slot_name = "does_not_exist"

    original_model = VALID_MINIMAL_METADATA_MODEL
    original_schema_view = original_model.schema_view

    with pytest.raises(ClassSlotNotFoundError):
        delete_class_slot(
            schema_view=original_schema_view, class_name=class_name, slot_name=slot_name
        )


def test_add_slot_usage_annotation():
    """Test the happy path of using add_slot_usage_annotation."""

    class_name = "Dataset"
    slot_name = "files"
    annotation_key = "usage"
    annotation_value = "required"

    original_model = VALID_MINIMAL_METADATA_MODEL
    original_schema_view = original_model.schema_view

    updated_schema_view = add_slot_usage_annotation(
        schema_view=original_schema_view,
        class_name=class_name,
        slot_name=slot_name,
        annotation_key=annotation_key,
        annotation_value=annotation_value,
    )

    # check that annotations are correctly compiled to yaml level:
    model_dict = updated_schema_view.export_model().as_dict()
    assert (
        model_dict["classes"][class_name]["slot_usage"][slot_name]["annotations"][
            annotation_key
        ]["value"]
        == annotation_value
    )


def test_disable_identifier_slot():
    """Test the happy path of using disable_identifier_slot."""

    class_name = "Dataset"

    original_model = VALID_MINIMAL_METADATA_MODEL
    original_schema_view = original_model.schema_view

    updated_schema_view = disable_identifier_slot(
        schema_view=original_schema_view,
        class_name=class_name,
    )
    updated_model = updated_schema_view.export_model()

    # check that the slot is correctly disabled:
    assert get_class_identifier(model=updated_model, class_name=class_name) is None
