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


from metldata.model_utils.essentials import MetadataModel
from metldata.model_utils.manipulate import delete_class_slot


def delete_class_slots_from_model(
    model: MetadataModel, class_slots: dict[str, list[str]]
) -> MetadataModel:
    """Delete the specified class slots from the provided model. Returns a modified
    copy of the model.
    """
    schema_view = model.schema_view

    for class_name, slot_names in class_slots.items():
        for slot_name in slot_names:
            schema_view = delete_class_slot(
                schema_view=schema_view, class_name=class_name, slot_name=slot_name
            )

    return schema_view.export_model()
