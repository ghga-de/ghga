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

"""Logic for checking transformation-specific model assumptions."""


from metldata.model_utils.assumptions import check_class_slot_exists
from metldata.model_utils.essentials import MetadataModel


def check_model_class_slots(model: MetadataModel, class_slots: dict[str, list[str]]):
    """Check that the specified classes and slots exist in the model."""
    for class_name, slot_names in class_slots.items():
        for slot_name in slot_names:
            check_class_slot_exists(
                model=model, class_name=class_name, slot_name=slot_name
            )
