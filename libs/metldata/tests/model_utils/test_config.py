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

"""Testing the metadata validator."""

from contextlib import nullcontext

import pytest

from metldata.model_utils.assumptions import MetadataModelAssumptionError
from metldata.model_utils.config import MetadataModelConfig
from metldata.model_utils.essentials import MetadataModel
from tests.fixtures.metadata_models import (
    INVALID_METADATA_MODELS,
    VALID_METADATA_MODELS,
)


@pytest.mark.parametrize(
    "model, is_valid",
    [(valid_model, True) for valid_model in VALID_METADATA_MODELS]
    + [(invalid_model, False) for invalid_model in INVALID_METADATA_MODELS],
)
def test_config(model: MetadataModel, is_valid: bool):
    """Test with valid and invalid model."""

    with model.temporary_yaml_path() as model_path:
        with nullcontext() if is_valid else pytest.raises(  # type:ignore
            MetadataModelAssumptionError
        ):
            config = MetadataModelConfig(metadata_model_path=model_path)
            _ = config.metadata_model
