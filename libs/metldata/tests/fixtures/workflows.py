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

"""Fixtures for workflows of trandformation steps."""

from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel

from metldata.builtin_transformations.delete_slots import SLOT_DELETION_TRANSFORMATION
from metldata.builtin_transformations.infer_references import (
    REFERENCE_INFERENCE_TRANSFORMATION,
)
from metldata.builtin_workflows.ghga_archive import GHGA_ARCHIVE_WORKFLOW
from metldata.custom_types import Json
from metldata.event_handling.models import SubmissionAnnotation
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import WorkflowDefinition, WorkflowStep
from tests.fixtures.utils import BASE_DIR, read_yaml

Config = TypeVar("Config", bound=BaseModel)

EXAMPLE_WORKFLOW_DEFINITION = WorkflowDefinition(
    description="A workflow for testing.",
    steps={
        "infer_references": WorkflowStep(
            description="A step for inferring references.",
            transformation_definition=REFERENCE_INFERENCE_TRANSFORMATION,
            input=None,
        ),
        "delete_slots": WorkflowStep(
            description="A step for deleting slots.",
            transformation_definition=SLOT_DELETION_TRANSFORMATION,
            input="infer_references",
        ),
    },
    artifacts={
        "inferred_and_restricted": "infer_references",
        "inferred_and_public": "delete_slots",
    },
)


@dataclass(frozen=True)
class WorkflowTestCase(Generic[Config]):
    """A test case for a workflow."""

    workflow_name: str
    case_name: str
    workflow_definition: WorkflowDefinition
    config: Config
    original_model: MetadataModel
    original_metadata: Json
    submission_annotation: SubmissionAnnotation
    artifact_models: dict[str, MetadataModel]
    artifact_metadata: dict[str, Json]

    def __str__(self) -> str:
        return f"{self.workflow_name}-{self.case_name}"


def _read_test_case(
    *,
    workflow_name: str,
    workflow_definition: WorkflowDefinition,
    case_name: str,
) -> WorkflowTestCase[Config]:
    """Read a test case for a workflow."""

    case_dir = BASE_DIR / "workflows" / workflow_name / case_name
    config_path = case_dir / "config.yaml"
    original_model_path = case_dir / "original_model.yaml"
    original_metadata_path = case_dir / "original_metadata.yaml"
    metadata_annotation_path = case_dir / "metadata_annotation.yaml"
    artifacts_dir = case_dir / "artifacts"

    artifact_models: dict[str, MetadataModel] = {}
    artifact_metadata: dict[str, Json] = {}

    for artifact in workflow_definition.artifacts:
        artifact_dir = artifacts_dir / artifact
        if artifact_dir.exists():
            model_path = artifact_dir / "transformed_model.yaml"
            if model_path.exists():
                artifact_models[artifact] = MetadataModel.init_from_path(model_path)
            metadata_path = artifact_dir / "transformed_metadata.yaml"
            if metadata_path.exists():
                artifact_metadata[artifact] = read_yaml(metadata_path)

    return WorkflowTestCase(
        workflow_name=workflow_name,
        case_name=case_name,
        workflow_definition=workflow_definition,
        config=workflow_definition.config_cls(**read_yaml(config_path)),  # type: ignore
        original_model=MetadataModel.init_from_path(original_model_path),
        original_metadata=read_yaml(original_metadata_path),
        submission_annotation=(
            SubmissionAnnotation(**read_yaml(metadata_annotation_path))
            if metadata_annotation_path.exists()
            else SubmissionAnnotation(accession_map={})
        ),
        artifact_models=artifact_models,
        artifact_metadata=artifact_metadata,
    )


def _read_all_test_cases_for_a_workflow(
    *,
    workflow_name: str,
    workflow_definition: WorkflowDefinition,
) -> list[WorkflowTestCase]:
    """Read all test cases for a workflow."""

    base_dir = BASE_DIR / "workflows" / workflow_name
    case_names = [path.name for path in base_dir.iterdir() if path.is_dir()]

    return [
        _read_test_case(
            workflow_name=workflow_name,
            workflow_definition=workflow_definition,
            case_name=case_name,
        )
        for case_name in case_names
    ]


def _read_all_test_cases(
    *, workflows_by_name: dict[str, WorkflowDefinition]
) -> list[WorkflowTestCase]:
    """Read all test cases for the specified workflows."""

    return [
        test_case
        for workflow_name, workflow_definition in workflows_by_name.items()
        for test_case in _read_all_test_cases_for_a_workflow(
            workflow_name=workflow_name,
            workflow_definition=workflow_definition,
        )
    ]


WORKFLOWS_BY_NAME: dict[str, WorkflowDefinition] = {
    "example_workflow": EXAMPLE_WORKFLOW_DEFINITION,
    "ghga_archive_workflow": GHGA_ARCHIVE_WORKFLOW,
}

WORKFLOW_TEST_CASES = _read_all_test_cases(workflows_by_name=WORKFLOWS_BY_NAME)

EXAMPLE_WORKFLOW_TEST_CASE = [
    test_case
    for test_case in WORKFLOW_TEST_CASES
    if test_case.workflow_name == "example_workflow"
][0]
EXAMPLE_ARTIFACT_MODELS = EXAMPLE_WORKFLOW_TEST_CASE.artifact_models
EXAMPLE_ARTIFACTS = EXAMPLE_WORKFLOW_TEST_CASE.artifact_metadata
