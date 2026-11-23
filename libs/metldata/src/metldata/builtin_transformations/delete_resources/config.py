# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ResourceDeletionConfig(BaseSettings):
    """Config containing the slot values that mark resources for deletion."""

    model_config = SettingsConfigDict(extra="forbid")

    resources_to_delete: dict[str, dict[str, Any]] = Field(
        ...,
        description=(
            "Per class, the slot values that mark a resource for deletion."
            + " A resource is deleted when every listed slot equals the given value."
            + " References to deleted resources are removed from all other classes."
        ),
        examples=[{"ResearchDataFile": {"included_in_submission": False}}],
    )
