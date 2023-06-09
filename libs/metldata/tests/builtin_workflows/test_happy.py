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

"""Test the builtin workflows using pre-defined test cases."""

import pytest

from metldata.transform.handling import WorkflowHandler
from tests.fixtures.workflows import WORKFLOW_TEST_CASES, WorkflowTestCase


@pytest.mark.parametrize(
    "test_case",
    WORKFLOW_TEST_CASES,
    ids=str,
)
def test_model_transform(
    test_case: WorkflowTestCase,
):
    """Test the happy path of transforming a model."""

    handler = WorkflowHandler(
        workflow_definition=test_case.workflow_definition,
        workflow_config=test_case.config,
        original_model=test_case.original_model,
    )
    artifact_models = handler.artifact_models

    for artifact, expected_model in test_case.artifact_models.items():
        assert artifact_models[artifact] == expected_model


@pytest.mark.parametrize("test_case", WORKFLOW_TEST_CASES, ids=str)
def test_metadata_transform(
    test_case: WorkflowTestCase,
):
    """Test the happy path of transforming metadata for a model."""

    handler = WorkflowHandler(
        workflow_definition=test_case.workflow_definition,
        workflow_config=test_case.config,
        original_model=test_case.original_model,
    )
    artifact_metadata = handler.run(
        metadata=test_case.original_metadata, annotation=test_case.submission_annotation
    )

    for artifact, expected_metadata in test_case.artifact_metadata.items():
        assert artifact_metadata[artifact] == expected_metadata
