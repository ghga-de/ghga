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

"""Testing the event publisher."""

import json

from ghga_service_commons.utils.utc_dates import now_as_utc

from metldata.config import SubmissionConfig
from metldata.event_handling.event_handling import FileSystemEventPublisher
from metldata.submission_registry import models
from metldata.submission_registry.event_publisher import SourceEventPublisher
from tests.fixtures.config import config_sub_fixture  # noqa: F401
from tests.fixtures.event_handling import file_system_event_fixture  # noqa: F401
from tests.fixtures.event_handling import Event, FileSystemEventFixture


def check_source_events(
    *,
    expected_submissions: list[models.Submission],
    source_event_topic: str,
    source_event_type: str,
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Check the content of a source event.

    Raises:
        AssertionError: if it does not match the expectations.
        EventNotPublishedError: if the event was not yet published.
    """

    expected_events = [
        Event(
            topic=source_event_topic,
            type_=source_event_type,
            key=expected_submission.id,
            payload=json.loads(expected_submission.json()),
        )
        for expected_submission in expected_submissions
    ]

    file_system_event_fixture.expect_events(expected_events=expected_events)


def test_happy(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test the happy path of publishing a submission."""

    provider = FileSystemEventPublisher(config=file_system_event_fixture.config)
    event_publisher = SourceEventPublisher(config=config_sub_fixture, provider=provider)

    # publish a submission:
    submission = models.Submission(
        id="submission001",
        title="test",
        description="test",
        content={"test_class": [{"alias": "test_alias1"}]},
        accession_map={"test_class": {"test_alias1": "test_accession1"}},
        status_history=(
            models.StatusChange(
                timestamp=now_as_utc(), new_status=models.SubmissionStatus.PENDING
            ),
        ),
    )
    event_publisher.publish_submission(submission)

    # check published source event:
    check_source_events(
        expected_submissions=[submission],
        source_event_topic=config_sub_fixture.source_event_topic,
        source_event_type=config_sub_fixture.source_event_type,
        file_system_event_fixture=file_system_event_fixture,
    )
