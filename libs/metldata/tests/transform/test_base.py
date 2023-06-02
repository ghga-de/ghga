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

"""Test the base module."""


import pytest
from pydantic import ValidationError

from metldata.builtin_transformations.delete_slots import SLOT_DELETION_TRANSFORMATION
from metldata.builtin_transformations.infer_references import (
    REFERENCE_INFERENCE_TRANSFORMATION,
)
from metldata.transform.base import WorkflowDefinition, WorkflowStep
from tests.fixtures.workflows import EXAMPLE_WORKFLOW_DEFINITION


def test_workflow_definition_invalid_step_refs():
    """Test that an invalid step reference raises an error."""
    with pytest.raises(ValidationError):
        WorkflowDefinition(
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
                    input="non_existing_step",
                ),
            },
            artifacts={
                "inferred_and_restricted": "infer_references",
                "inferred_and_public": "delete_slots",
            },
        )


def test_workflow_definition_invalid_multiple_first_steps():
    """Test that specifing multiple steps without input raises an exeception."""
    with pytest.raises(ValidationError):
        WorkflowDefinition(
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
                    input=None,
                ),
            },
            artifacts={
                "inferred_and_restricted": "infer_references",
                "inferred_and_public": "delete_slots",
            },
        )


def test_workflow_definition_invalid_artifacts():
    """Test that artifacts referencing non-existing steps raise an exception."""
    with pytest.raises(ValidationError):
        WorkflowDefinition(
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
                    input=None,
                ),
            },
            artifacts={
                "inferred_and_restricted": "non_existing_step",
                "inferred_and_public": "delete_slots",
            },
        )


def test_workflow_definition_config_cls():
    """Test that the config_cls of the WorkflowDefinition generates a concatenated
    config class correctly."""

    config_fields = EXAMPLE_WORKFLOW_DEFINITION.config_cls.__fields__

    assert "infer_references" in config_fields
    assert "delete_slots" in config_fields
    assert (
        config_fields["infer_references"].type_
        == REFERENCE_INFERENCE_TRANSFORMATION.config_cls
    )
    assert (
        config_fields["delete_slots"].type_ == SLOT_DELETION_TRANSFORMATION.config_cls
    )


def test_workflow_definition_step_order_happy():
    """Test that the step order is correctly inferred from the workflow definition."""

    workflow_definition = WorkflowDefinition(
        description="A workflow for testing.",
        steps={
            "step3": WorkflowStep(
                description="A test step.",
                transformation_definition=SLOT_DELETION_TRANSFORMATION,
                input="step2",
            ),
            "step2": WorkflowStep(
                description="A test step.",
                transformation_definition=SLOT_DELETION_TRANSFORMATION,
                input="step1",
            ),
            "step1": WorkflowStep(
                description="A test step.",
                transformation_definition=SLOT_DELETION_TRANSFORMATION,
                input=None,
            ),
            "step4": WorkflowStep(
                description="A test step.",
                transformation_definition=SLOT_DELETION_TRANSFORMATION,
                input="step2",
            ),
        },
        artifacts={
            "output3": "step3",
            "output4": "step4",
        },
    )

    assert workflow_definition.step_order in (
        [
            "step1",
            "step2",
            "step3",
            "step4",
        ],
        [
            "step1",
            "step2",
            "step4",
            "step3",
        ],
    )


def test_workflow_definition_step_order_circular():
    """Test that the step order is correctly inferred from the workflow definition."""

    workflow_definition = WorkflowDefinition(
        description="A workflow for testing.",
        steps={
            "step1": WorkflowStep(
                description="A test step.",
                transformation_definition=SLOT_DELETION_TRANSFORMATION,
                input=None,
            ),
            "step2": WorkflowStep(
                description="A test step.",
                transformation_definition=SLOT_DELETION_TRANSFORMATION,
                input="step4",
            ),
            "step3": WorkflowStep(
                description="A test step.",
                transformation_definition=SLOT_DELETION_TRANSFORMATION,
                input="step2",
            ),
            "step4": WorkflowStep(
                description="A test step.",
                transformation_definition=SLOT_DELETION_TRANSFORMATION,
                input="step3",
            ),
        },
        artifacts={
            "output3": "step3",
            "output4": "step4",
        },
    )

    with pytest.raises(RuntimeError):
        workflow_definition.step_order
