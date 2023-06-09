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

"""Test the main module."""

import json

import pytest

from metldata.event_handling.models import SubmissionEventPayload
from metldata.submission_registry import get_artifact_topic
from metldata.transform.main import (
    TransformationEventHandlingConfig,
    run_workflow_on_all_source_events,
)
from tests.fixtures.event_handling import file_system_event_fixture  # noqa: F401
from tests.fixtures.event_handling import Event, FileSystemEventFixture
from tests.fixtures.workflows import (
    EXAMPLE_WORKFLOW_DEFINITION,
    EXAMPLE_WORKFLOW_TEST_CASE,
)


@pytest.mark.asyncio
async def test_run_workflow_on_all_source_events(
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test the happy path of using the run_workflow_on_all_source_events function."""

    event_config = TransformationEventHandlingConfig(
        artifact_topic_prefix="artifacts",
        source_event_topic="source-events",
        source_event_type="source-event",
        **file_system_event_fixture.config.dict(),
    )

    submission_id = "some-submission-id"
    source_event = Event(
        topic=event_config.source_event_topic,
        type_=event_config.source_event_type,
        key=submission_id,
        payload=json.loads(
            SubmissionEventPayload(
                submission_id=submission_id,
                content=EXAMPLE_WORKFLOW_TEST_CASE.original_metadata,
                annotation=EXAMPLE_WORKFLOW_TEST_CASE.submission_annotation,
            ).json()
        ),
    )
    await file_system_event_fixture.publish_events(events=[source_event])

    expected_events = [
        Event(
            topic=get_artifact_topic(
                artifact_topic_prefix=event_config.artifact_topic_prefix,
                artifact_type=artifact_type,
            ),
            type_=artifact_type,
            key=submission_id,
            payload=json.loads(
                SubmissionEventPayload(
                    submission_id=submission_id,
                    content=artifact,
                    annotation=EXAMPLE_WORKFLOW_TEST_CASE.submission_annotation,
                ).json()
            ),
        )
        for artifact_type, artifact in EXAMPLE_WORKFLOW_TEST_CASE.artifact_metadata.items()
    ]

    await run_workflow_on_all_source_events(
        event_config=event_config,
        workflow_definition=EXAMPLE_WORKFLOW_DEFINITION,
        worflow_config=EXAMPLE_WORKFLOW_TEST_CASE.config,
        original_model=EXAMPLE_WORKFLOW_TEST_CASE.original_model,
    )

    file_system_event_fixture.expect_events(expected_events=expected_events)
