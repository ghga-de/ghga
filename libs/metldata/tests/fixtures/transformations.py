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

"""Transformation test cases."""

from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar

import yaml
from pydantic import BaseModel

from metldata.builtin_transformations.infer_references import ReferenceInferenceConfig
from metldata.custom_types import Json
from metldata.model_utils.essentials import MetadataModel
from tests.fixtures.utils import BASE_DIR

Config = TypeVar("Config", bound=BaseModel)


@dataclass(frozen=True)
class TransformationTestCase(Generic[Config]):
    """A test case for a transformation."""

    config: Config
    original_model: MetadataModel
    original_metadata: Json
    transformed_model: MetadataModel
    transformed_metadata: Json


def _read_yaml(path: Path) -> Json:
    """Read a YAML file."""

    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _read_test_case(
    config_class: type[Config], transformation_name: str, case_name: str
) -> TransformationTestCase[Config]:
    """Read a test case for a transformation."""

    case_dir = BASE_DIR / "transformations" / transformation_name / case_name
    config_path = case_dir / "config.yaml"
    original_model_path = case_dir / "original_model.yaml"
    original_metadata_path = case_dir / "original_metadata.yaml"
    transformed_model_path = case_dir / "transformed_model.yaml"
    transformed_metadata_path = case_dir / "transformed_metadata.yaml"

    return TransformationTestCase(
        config=config_class(**_read_yaml(config_path)),
        original_model=MetadataModel.init_from_path(original_model_path),
        original_metadata=_read_yaml(original_metadata_path),
        transformed_model=MetadataModel.init_from_path(transformed_model_path),
        transformed_metadata=_read_yaml(transformed_metadata_path),
    )


def _read_all_test_cases(
    config_class: type[Config], transformation_name: str
) -> list[TransformationTestCase[Config]]:
    """Read all test cases for a transformation."""

    base_dir = BASE_DIR / "transformations" / transformation_name
    case_names = [path.name for path in base_dir.iterdir() if path.is_dir()]

    return [
        _read_test_case(
            config_class=config_class,
            transformation_name=transformation_name,
            case_name=case_name,
        )
        for case_name in case_names
    ]


INFERRED_REFERENCE_TEST_CASES = _read_all_test_cases(
    config_class=ReferenceInferenceConfig,
    transformation_name="infer_references",
)
