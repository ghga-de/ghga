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


class AccessionAdditionConfig(BaseSettings):
    """Config to add accessions to a model and associated metadata."""

    model_config = SettingsConfigDict(extra="forbid")

    accession_slot_name: str = Field(
        "accession", description="The name of the slot to contain the accessions to."
    )
    accession_slot_description: str = Field(
        "The accession for an entity.",
        description="The description of the slot to contain the accessions to.",
    )
