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
from typing import Generic, TypeVar

from pydantic import BaseModel

from metldata.builtin_transformations.add_accessions import (
    ACCESSION_ADDITION_TRANSFORMATION,
)
from metldata.builtin_transformations.custom_embeddings import (
    CUSTOM_EMBEDDING_TRANSFORMATION,
)
from metldata.builtin_transformations.delete_slots import SLOT_DELETION_TRANSFORMATION
from metldata.builtin_transformations.infer_references import (
    REFERENCE_INFERENCE_TRANSFORMATION,
)
from metldata.builtin_transformations.merge_slots import SLOT_MERGING_TRANSFORMATION
from metldata.custom_types import Json
from metldata.event_handling.models import SubmissionAnnotation
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import TransformationDefinition
from tests.fixtures.utils import BASE_DIR, read_yaml

Config = TypeVar("Config", bound=BaseModel)


@dataclass(frozen=True)
class TransformationTestCase(Generic[Config]):
    """A test case for a transformation."""

    transformation_name: str
    case_name: str
    transformation_definition: TransformationDefinition
    config: Config
    original_model: MetadataModel
    original_metadata: Json
    metadata_annotation: SubmissionAnnotation
    transformed_model: MetadataModel
    transformed_metadata: Json

    def __str__(self) -> str:
        return f"{self.transformation_name}-{self.case_name}"


def _read_test_case(
    *,
    transformation_name: str,
    transformation_definition: TransformationDefinition,
    case_name: str,
) -> TransformationTestCase[Config]:
    """Read a test case for a transformation."""

    case_dir = BASE_DIR / "transformations" / transformation_name / case_name
    config_path = case_dir / "config.yaml"
    original_model_path = case_dir / "original_model.yaml"
    original_metadata_path = case_dir / "original_metadata.yaml"
    metadata_annotation_path = case_dir / "metadata_annotation.yaml"
    transformed_model_path = case_dir / "transformed_model.yaml"
    transformed_metadata_path = case_dir / "transformed_metadata.yaml"

    return TransformationTestCase(
        transformation_name=transformation_name,
        case_name=case_name,
        transformation_definition=transformation_definition,
        config=transformation_definition.config_cls(**read_yaml(config_path)),
        original_model=MetadataModel.init_from_path(original_model_path),
        original_metadata=read_yaml(original_metadata_path),
        metadata_annotation=(
            SubmissionAnnotation(**read_yaml(metadata_annotation_path))
            if metadata_annotation_path.exists()
            else SubmissionAnnotation(accession_map={})
        ),
        transformed_model=MetadataModel.init_from_path(transformed_model_path),
        transformed_metadata=read_yaml(transformed_metadata_path),
    )


def _read_all_test_cases_for_a_transformation(
    *,
    transformation_name: str,
    transformation_definition: TransformationDefinition,
) -> list[TransformationTestCase]:
    """Read all test cases for a transformation."""

    base_dir = BASE_DIR / "transformations" / transformation_name
    case_names = [path.name for path in base_dir.iterdir() if path.is_dir()]

    return [
        _read_test_case(
            transformation_name=transformation_name,
            transformation_definition=transformation_definition,
            case_name=case_name,
        )
        for case_name in case_names
    ]


def _read_all_test_cases(
    *, transformations_by_name: dict[str, TransformationDefinition]
) -> list[TransformationTestCase]:
    """Read all test cases for the specified transformations."""

    return [
        test_case
        for transformation_name, transformation_definition in transformations_by_name.items()
        for test_case in _read_all_test_cases_for_a_transformation(
            transformation_name=transformation_name,
            transformation_definition=transformation_definition,
        )
    ]


TRANSFORMATIONS_BY_NAME: dict[str, TransformationDefinition] = {
    "add_accessions": ACCESSION_ADDITION_TRANSFORMATION,
    "infer_references": REFERENCE_INFERENCE_TRANSFORMATION,
    "delete_slots": SLOT_DELETION_TRANSFORMATION,
    "custom_embedding": CUSTOM_EMBEDDING_TRANSFORMATION,
    "merge_slots": SLOT_MERGING_TRANSFORMATION,
}


TRANSFORMATION_TEST_CASES = _read_all_test_cases(
    transformations_by_name=TRANSFORMATIONS_BY_NAME
)
