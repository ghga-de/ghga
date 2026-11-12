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

"""Config Parameter Modeling and Parsing"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

from metldata.model_utils.assumptions import (
    check_basic_model_assumption,
    check_dataset_anchor,
    check_study_anchor,
    check_study_cardinality,
)
from metldata.model_utils.essentials import MetadataModel


class ModelClassesConfig(BaseSettings):
    """The classes of the metadata model whose entities take the study and dataset
    PIDs, which loading the model checks.
    """

    study_class_name: str = Field(
        default="Study",
        description=(
            "Name of the metadata model class whose entity takes the study PID. The"
            + " model must anchor it on the 'studies' slot."
        ),
    )

    dataset_class_name: str = Field(
        default="Dataset",
        description=(
            "Name of the metadata model class whose entities take dataset PIDs. The"
            + " model must anchor it."
        ),
    )


class MetadataModelConfig(ModelClassesConfig):
    """Config parameters and their defaults."""

    metadata_model_path: Path = Field(
        ..., description="The path to the metadata model defined in LinkML."
    )

    @property
    def metadata_model(self) -> MetadataModel:
        """Load the submission model from the path and check that it meets the basic
        assumptions, holds exactly one study per submission and anchors the dataset
        class.
        """
        model = MetadataModel.init_from_path(self.metadata_model_path)
        check_basic_model_assumption(model)
        # check_study_cardinality only looks at the STUDY_ANCHOR slot, not at the class
        # it holds, so check_study_anchor must run first
        check_study_anchor(model=model, study_class_name=self.study_class_name)
        check_study_cardinality(model)
        check_dataset_anchor(model=model, dataset_class_name=self.dataset_class_name)
        return model
