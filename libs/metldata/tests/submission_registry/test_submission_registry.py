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

"""Test the submission registry."""


import pytest

from metldata.config import Config
from metldata.submission_registry import models
from metldata.submission_registry.event_publisher import EventPublisher
from metldata.submission_registry.submission_registry import SubmissionRegistry
from metldata.submission_registry.submission_store import SubmissionStore
from tests.fixtures.config import config_fixture  # noqa: F401
from tests.fixtures.metadata import (
    INVALID_MINIMAL_METADATA_EXAMPLES,
    VALID_MINIMAL_METADATA_EXAMPLES,
)
from tests.fixtures.utils import check_source_event, does_event_exist


def test_happy(config_fixture: Config):  # noqa: F811
    """Test the happy path of using the submission registry."""

    # inject dependencies:
    submission_store = SubmissionStore(config=config_fixture)
    event_publisher = EventPublisher(config=config_fixture)
    submission_registry = SubmissionRegistry(
        config=config_fixture,
        submission_store=submission_store,
        event_publisher=event_publisher,
    )

    # create a new submission:
    submission_header = models.SubmissionHeader(title="test", description="test")
    submission_id = submission_registry.init_submission(header=submission_header)

    # check submission in store:
    observed_submission = submission_store.get_by_id(submission_id)
    assert observed_submission.title == submission_header.title
    assert observed_submission.description == submission_header.description
    assert observed_submission.content is None
    assert observed_submission.current_status == models.SubmissionStatus.PENDING

    # check that source event is not yet present:
    assert not does_event_exist(
        submission_id=observed_submission.id,
        source_events_dir=config_fixture.source_events_dir,
    )

    # provide content:
    submission_content = VALID_MINIMAL_METADATA_EXAMPLES[0]
    submission_registry.upsert_submission_content(
        submission_id=submission_id, content=submission_content
    )

    # check submission in store:
    observed_submission = submission_store.get_by_id(submission_id)
    assert observed_submission.content == submission_content
    assert observed_submission.current_status == models.SubmissionStatus.PENDING

    # update content:
    submission_content_updated = VALID_MINIMAL_METADATA_EXAMPLES[1]
    submission_registry.upsert_submission_content(
        submission_id=submission_id, content=submission_content_updated
    )

    # check submission in store:
    observed_submission = submission_store.get_by_id(submission_id)
    assert observed_submission.content == submission_content_updated
    assert observed_submission.current_status == models.SubmissionStatus.PENDING

    # check published source event:
    check_source_event(
        expected_content=observed_submission,
        source_events_dir=config_fixture.source_events_dir,
    )

    # declare submission is complete:
    submission_registry.complete_submission(id_=submission_id)

    # check submission in store:
    observed_submission = submission_store.get_by_id(submission_id)
    assert observed_submission.current_status == models.SubmissionStatus.COMPLETED

    # check published source event:
    check_source_event(
        expected_content=observed_submission,
        source_events_dir=config_fixture.source_events_dir,
    )


def test_failed_content_validation(config_fixture: Config):  # noqa: F811
    """Test that invalid content cannot be upserted."""

    # inject dependencies:
    submission_store = SubmissionStore(config=config_fixture)
    event_publisher = EventPublisher(config=config_fixture)
    submission_registry = SubmissionRegistry(
        config=config_fixture,
        submission_store=submission_store,
        event_publisher=event_publisher,
    )

    # create a new submission:
    submission_header = models.SubmissionHeader(title="test", description="test")
    submission_id = submission_registry.init_submission(header=submission_header)

    # check submission in store:
    observed_submission_original = submission_store.get_by_id(submission_id)

    # provide invalid content:
    submission_content = INVALID_MINIMAL_METADATA_EXAMPLES[0]
    with pytest.raises(SubmissionRegistry.ValidationError):
        submission_registry.upsert_submission_content(
            submission_id=submission_id, content=submission_content
        )

    # check that the submission was not changed:
    observed_submission_updated = submission_store.get_by_id(submission_id)
    assert observed_submission_original == observed_submission_updated


def test_update_after_completion(config_fixture: Config):  # noqa: F811
    """Test no updates can be carried out after completion."""

    # inject dependencies:
    submission_store = SubmissionStore(config=config_fixture)
    event_publisher = EventPublisher(config=config_fixture)
    submission_registry = SubmissionRegistry(
        config=config_fixture,
        submission_store=submission_store,
        event_publisher=event_publisher,
    )

    # create a new submission:
    submission_header = models.SubmissionHeader(title="test", description="test")
    submission_id = submission_registry.init_submission(header=submission_header)

    # provide content:
    submission_content = VALID_MINIMAL_METADATA_EXAMPLES[0]
    submission_registry.upsert_submission_content(
        submission_id=submission_id, content=submission_content
    )

    # check submission in store:
    observed_submission = submission_store.get_by_id(submission_id)

    # declare submission is complete:
    submission_registry.complete_submission(id_=submission_id)

    # try to update content:
    submission_content_updated = VALID_MINIMAL_METADATA_EXAMPLES[1]
    with pytest.raises(SubmissionRegistry.StatusError):
        submission_registry.upsert_submission_content(
            submission_id=submission_id, content=submission_content_updated
        )

    # check that the submission content did not change:
    observed_submission = submission_store.get_by_id(submission_id)
    assert observed_submission.content == submission_content
