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

"""Config parameters and their defaults."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SlotDeletionConfig(BaseSettings):
    """Config containing slots to be deleted from models and associated metadata."""

    model_config = SettingsConfigDict(extra="forbid")

    slots_to_delete: dict[str, list[str]] = Field(
        ...,
        description=(
            "A nested dictionary specifying slots that should be deleted per class."
            + " The keys refer to classes, the values to the slots that should be"
            + " deleted from the respective class."
        ),
        examples=[
            {
                "class_a": ["some_slot", "another_slot"],
                "class_b": ["some_slot"],
                "class_c": ["some_slot", "yet_another_slot"],
            }
        ],
    )
