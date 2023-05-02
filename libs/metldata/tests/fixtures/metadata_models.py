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

"""Metadata models."""

from metldata.model_utils.essentials import MetadataModel
from tests.fixtures.utils import BASE_DIR

EXAMPLE_MODEL_DIR = BASE_DIR / "example_models"
VALID_MINIMAL_MODEL_EXAMPLE_PATH = EXAMPLE_MODEL_DIR / "minimal_model.yaml"


def _get_example_model(name: str) -> MetadataModel:
    """Get example model."""

    return MetadataModel.init_from_path(EXAMPLE_MODEL_DIR / f"{name}.yaml")


VALID_MINIMAL_METADATA_MODEL = _get_example_model("minimal_model")
VALID_ADVANCED_METADATA_MODEL = _get_example_model("advanced_model")
VALID_METADATA_MODELS = [VALID_MINIMAL_METADATA_MODEL, VALID_ADVANCED_METADATA_MODEL]

ROOT_CLASS_INVALID_MODELS = [
    _get_example_model(f"minimal_model_root_class_missing{idx}") for idx in range(1, 3)
]

ANCHORS_INVALID_MODELS = [
    _get_example_model(f"minimal_model_anchors_invalid{idx}") for idx in range(1, 5)
]

INVALID_METADATA_MODELS = ROOT_CLASS_INVALID_MODELS + ANCHORS_INVALID_MODELS
