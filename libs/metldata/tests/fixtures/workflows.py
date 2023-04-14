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

from metldata.builtin_transformations.delete_slots import slot_deletion_transformation
from metldata.builtin_transformations.infer_references import (
    reference_inference_transformation,
)
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.base import WorkflowDefinition, WorkflowStep
from tests.fixtures.utils import BASE_DIR, read_yaml

EXAMPLE_WORKFLOW_JOB_DIR = BASE_DIR / "example_workflow"

EXAMPLE_WORKFLOW_DEFINITION = WorkflowDefinition(
    description="A workflow for testing.",
    steps={
        "infer_references": WorkflowStep(
            description="A step for inferring references.",
            transformation_definition=reference_inference_transformation,
            input=None,
        ),
        "delete_slots": WorkflowStep(
            description="A step for deleting slots.",
            transformation_definition=slot_deletion_transformation,
            input="infer_references",
        ),
    },
    artifacts={
        "inferred_and_restricted": "infer_references",
        "inferred_and_public": "delete_slots",
    },
)

EXAMPLE_CONFIG = EXAMPLE_WORKFLOW_DEFINITION.config_cls(
    **read_yaml(EXAMPLE_WORKFLOW_JOB_DIR / "config.yaml")
)
EXAMPLE_ORIGINAL_MODEL = MetadataModel.init_from_path(
    EXAMPLE_WORKFLOW_JOB_DIR / "original_model.yaml"
)
EXAMPLE_ORIGINAL_METADATA = read_yaml(
    EXAMPLE_WORKFLOW_JOB_DIR / "original_metadata.yaml"
)
EXAMPLE_ARTIFACT_MODELS = {
    artifact_name: MetadataModel.init_from_path(
        EXAMPLE_WORKFLOW_JOB_DIR
        / "artifacts"
        / artifact_name
        / "transformed_model.yaml"
    )
    for artifact_name in EXAMPLE_WORKFLOW_DEFINITION.artifacts
}
EXAMPLE_ARTIFACTS = {
    artifact_name: read_yaml(
        EXAMPLE_WORKFLOW_JOB_DIR
        / "artifacts"
        / artifact_name
        / "transformed_metadata.yaml"
    )
    for artifact_name in EXAMPLE_WORKFLOW_DEFINITION.artifacts
}
