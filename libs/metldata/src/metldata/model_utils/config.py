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

"""Config Parameter Modeling and Parsing"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

from metldata.model_utils.assumptions import check_basic_model_assumption
from metldata.model_utils.essentials import MetadataModel


class MetadataModelConfig(BaseSettings):
    """Config parameters and their defaults."""

    metadata_model_path: Path = Field(
        ..., description="The path to the metadata model defined in LinkML."
    )

    @property
    def metadata_model(self) -> MetadataModel:
        """Load the model from the path and check basic assumptions."""
        model = MetadataModel.init_from_path(self.metadata_model_path)
        check_basic_model_assumption(model)
        return model
