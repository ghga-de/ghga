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

from metldata.accession_registry.accession_registry import AccessionRegistry
from metldata.accession_registry.accession_store import AccessionStore
from metldata.config import SubmissionConfig
from metldata.event_handling.event_handling import FileSystemEventPublisher
from metldata.submission_registry import models
from metldata.submission_registry.event_publisher import SourceEventPublisher
from metldata.submission_registry.submission_registry import SubmissionRegistry
from metldata.submission_registry.submission_store import SubmissionStore
from tests.fixtures.config import config_sub_fixture  # noqa: F401
from tests.fixtures.event_handling import file_system_event_fixture  # noqa: F401
from tests.fixtures.event_handling import FileSystemEventFixture
from tests.fixtures.metadata import (
    INVALID_MINIMAL_METADATA_EXAMPLES,
    VALID_MINIMAL_METADATA_EXAMPLES,
)
from tests.submission_registry.test_event_publisher import check_source_events


def test_happy(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test the happy path of using the submission registry."""

    # inject dependencies:
    submission_store = SubmissionStore(config=config_sub_fixture)
    provider = FileSystemEventPublisher(config=file_system_event_fixture.config)
    event_publisher = SourceEventPublisher(config=config_sub_fixture, provider=provider)
    accession_store = AccessionStore(config=config_sub_fixture)
    accession_registry = AccessionRegistry(
        config=config_sub_fixture, accession_store=accession_store
    )
    submission_registry = SubmissionRegistry(
        config=config_sub_fixture,
        submission_store=submission_store,
        event_publisher=event_publisher,
        accession_registry=accession_registry,
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

    # check accessions are in store:
    for class_ in observed_submission.accession_map.values():
        for accession in class_.values():
            assert accession_store.exists(accession=accession)

    # check published source event:
    check_source_events(
        expected_submissions=[observed_submission],
        source_event_topic=config_sub_fixture.source_event_topic,
        source_event_type=config_sub_fixture.source_event_type,
        file_system_event_fixture=file_system_event_fixture,
    )

    # declare submission is complete:
    submission_registry.complete_submission(id_=submission_id)

    # check submission in store:
    observed_submission = submission_store.get_by_id(submission_id)
    assert observed_submission.current_status == models.SubmissionStatus.COMPLETED

    # check published source event:
    check_source_events(
        expected_submissions=[observed_submission],
        source_event_topic=config_sub_fixture.source_event_topic,
        source_event_type=config_sub_fixture.source_event_type,
        file_system_event_fixture=file_system_event_fixture,
    )


def test_failed_content_validation(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test that invalid content cannot be upserted."""

    # inject dependencies:
    submission_store = SubmissionStore(config=config_sub_fixture)
    provider = FileSystemEventPublisher(config=file_system_event_fixture.config)
    event_publisher = SourceEventPublisher(config=config_sub_fixture, provider=provider)
    accession_store = AccessionStore(config=config_sub_fixture)
    accession_registry = AccessionRegistry(
        config=config_sub_fixture, accession_store=accession_store
    )
    submission_registry = SubmissionRegistry(
        config=config_sub_fixture,
        submission_store=submission_store,
        event_publisher=event_publisher,
        accession_registry=accession_registry,
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


def test_update_after_completion(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test no updates can be carried out after completion."""

    # inject dependencies:
    submission_store = SubmissionStore(config=config_sub_fixture)
    provider = FileSystemEventPublisher(config=file_system_event_fixture.config)
    event_publisher = SourceEventPublisher(config=config_sub_fixture, provider=provider)
    accession_store = AccessionStore(config=config_sub_fixture)
    accession_registry = AccessionRegistry(
        config=config_sub_fixture, accession_store=accession_store
    )
    submission_registry = SubmissionRegistry(
        config=config_sub_fixture,
        submission_store=submission_store,
        event_publisher=event_publisher,
        accession_registry=accession_registry,
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
