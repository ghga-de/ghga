# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from ghga_service_commons.utils.utc_dates import now_as_utc
from metldata.accession_registry.accession_registry import AccessionRegistry
from metldata.accession_registry.accession_store import AccessionStore
from metldata.config import SubmissionConfig
from metldata.event_handling.event_handling import FileSystemEventPublisher
from metldata.submission_registry import models
from metldata.submission_registry.event_publisher import SourceEventPublisher
from metldata.submission_registry.submission_registry import SubmissionRegistry
from metldata.submission_registry.submission_store import SubmissionStore
from tests.fixtures.config import config_sub_fixture  # noqa: F401
from tests.fixtures.event_handling import (
    FileSystemEventFixture,
    file_system_event_fixture,  # noqa: F401
)
from tests.fixtures.metadata import (
    INVALID_MINIMAL_METADATA_WITH_STUDY_EXAMPLE,
    VALID_MINIMAL_METADATA_WITH_STUDY_EXAMPLES,
)
from tests.submission_registry.test_event_publisher import check_source_events


def test_happy(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test the happy path of using the submission registry."""
    config = config_sub_fixture
    submission_store, accession_store, submission_registry = build_submission_registry(
        config=config, event_fixture=file_system_event_fixture
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
    submission_content = VALID_MINIMAL_METADATA_WITH_STUDY_EXAMPLES[0]
    submission_registry.upsert_submission_content(
        submission_id=submission_id, content=submission_content
    )

    # check submission in store:
    observed_submission = submission_store.get_by_id(submission_id)
    assert observed_submission.content == submission_content
    assert observed_submission.current_status == models.SubmissionStatus.PENDING
    study_pid = observed_submission.accession_map["studies"]["test_study"]

    # update content:
    submission_content_updated = VALID_MINIMAL_METADATA_WITH_STUDY_EXAMPLES[1]
    submission_registry.upsert_submission_content(
        submission_id=submission_id, content=submission_content_updated
    )

    # check submission in store:
    observed_submission = submission_store.get_by_id(submission_id)
    assert observed_submission.content == submission_content_updated
    assert observed_submission.current_status == models.SubmissionStatus.PENDING

    # check the update kept the study PID, which every other accession derives from:
    assert observed_submission.accession_map["studies"]["test_study"] == study_pid
    for accessions_by_alias in observed_submission.accession_map.values():
        for accession in accessions_by_alias.values():
            assert accession.startswith(study_pid)

    # check only the random block of the study PID is registered, under its year:
    _, year, random_block, _ = study_pid.split(".")
    assert accession_store.get_random_blocks(year=year) == {random_block}

    # check published source event:
    check_source_events(
        expected_submissions=[observed_submission],
        source_event_topic=config.source_event_topic,
        source_event_type=config.source_event_type,
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
        source_event_topic=config.source_event_topic,
        source_event_type=config.source_event_type,
        file_system_event_fixture=file_system_event_fixture,
    )


@pytest.mark.parametrize(
    "submission_content",
    [
        INVALID_MINIMAL_METADATA_WITH_STUDY_EXAMPLE,
        {
            "studies": [{"alias": "shared"}],
            "files": [{"alias": "shared", "filename": "shared.fastq"}],
            "datasets": [],
        },
    ],
    ids=["invalid_against_model", "shared_alias"],
)
def test_failed_content_validation(
    submission_content: dict,
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test that invalid content cannot be upserted, and that no study PID is minted
    for it.
    """
    submission_store, accession_store, submission_registry = build_submission_registry(
        config=config_sub_fixture, event_fixture=file_system_event_fixture
    )

    # create a new submission:
    submission_header = models.SubmissionHeader(title="test", description="test")
    submission_id = submission_registry.init_submission(header=submission_header)

    # check submission in store:
    observed_submission_original = submission_store.get_by_id(submission_id)

    # provide invalid content:
    with pytest.raises(SubmissionRegistry.ValidationError):
        submission_registry.upsert_submission_content(
            submission_id=submission_id, content=submission_content
        )

    # check that the submission was not changed and no study PID was minted:
    observed_submission_updated = submission_store.get_by_id(submission_id)
    assert observed_submission_original == observed_submission_updated
    year = now_as_utc().strftime("%y")
    assert accession_store.get_random_blocks(year=year) == set()


def test_update_after_completion(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test no updates can be carried out after completion."""
    submission_store, _, submission_registry = build_submission_registry(
        config=config_sub_fixture, event_fixture=file_system_event_fixture
    )

    # create a new submission:
    submission_header = models.SubmissionHeader(title="test", description="test")
    submission_id = submission_registry.init_submission(header=submission_header)

    # provide content:
    submission_content = VALID_MINIMAL_METADATA_WITH_STUDY_EXAMPLES[0]
    submission_registry.upsert_submission_content(
        submission_id=submission_id, content=submission_content
    )

    # check submission in store:
    observed_submission = submission_store.get_by_id(submission_id)

    # declare submission is complete:
    submission_registry.complete_submission(id_=submission_id)

    # try to update content:
    submission_content_updated = VALID_MINIMAL_METADATA_WITH_STUDY_EXAMPLES[1]
    with pytest.raises(SubmissionRegistry.StatusError):
        submission_registry.upsert_submission_content(
            submission_id=submission_id, content=submission_content_updated
        )

    # check that the submission content did not change:
    observed_submission = submission_store.get_by_id(submission_id)
    assert observed_submission.content == submission_content


def build_submission_registry(
    *, config: SubmissionConfig, event_fixture: FileSystemEventFixture
) -> tuple[SubmissionStore, AccessionStore, SubmissionRegistry]:
    """Build the submission registry with its stores, which are returned too."""
    submission_store = SubmissionStore(config=config)
    provider = FileSystemEventPublisher(config=event_fixture.config)
    accession_store = AccessionStore(config=config)
    submission_registry = SubmissionRegistry(
        config=config,
        submission_store=submission_store,
        event_publisher=SourceEventPublisher(config=config, provider=provider),
        accession_registry=AccessionRegistry(
            config=config, accession_store=accession_store
        ),
    )
    return submission_store, accession_store, submission_registry


def test_reserve_study_pid(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test that a reserved study PID is registered and held by a pending submission
    without content, and that upserting the content keeps it under the study alias.
    """
    submission_store, accession_store, submission_registry = build_submission_registry(
        config=config_sub_fixture, event_fixture=file_system_event_fixture
    )

    submission_header = models.SubmissionHeader(title="internal name")
    submission_id, study_pid = submission_registry.reserve_study_pid(
        header=submission_header
    )

    observed_submission = submission_store.get_by_id(submission_id)
    assert observed_submission.title == submission_header.title
    assert observed_submission.content is None
    assert observed_submission.current_status == models.SubmissionStatus.PENDING
    assert observed_submission.accession_map == {"studies": {study_pid: study_pid}}
    _, year, random_block, _ = study_pid.split(".")
    assert accession_store.get_random_blocks(year=year) == {random_block}

    submission_registry.upsert_submission_content(
        submission_id=submission_id,
        content=VALID_MINIMAL_METADATA_WITH_STUDY_EXAMPLES[0],
    )

    accession_map = submission_store.get_by_id(submission_id).accession_map
    assert accession_map["studies"] == {"test_study": study_pid}
    # no second study PID was minted
    assert accession_store.get_random_blocks(year=year) == {random_block}


def test_check_study_pid(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test that the check passes for the study PID a pending submission holds,
    refuses the study PID of another submission, and refuses the submission once it
    is completed.
    """
    _, _, submission_registry = build_submission_registry(
        config=config_sub_fixture, event_fixture=file_system_event_fixture
    )
    header = models.SubmissionHeader(title="internal name")
    submission_id, study_pid = submission_registry.reserve_study_pid(header=header)
    _, other_study_pid = submission_registry.reserve_study_pid(header=header)

    submission_registry.check_study_pid(
        submission_id=submission_id, study_pid=study_pid
    )
    with pytest.raises(SubmissionRegistry.StudyPidMismatchError):
        submission_registry.check_study_pid(
            submission_id=submission_id, study_pid=other_study_pid
        )

    submission_registry.upsert_submission_content(
        submission_id=submission_id,
        content=VALID_MINIMAL_METADATA_WITH_STUDY_EXAMPLES[0],
    )
    submission_registry.complete_submission(id_=submission_id)
    with pytest.raises(SubmissionRegistry.StatusError):
        submission_registry.check_study_pid(
            submission_id=submission_id, study_pid=study_pid
        )


def test_get_pending_submissions(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test that every pending submission is listed with the study PID it holds, or
    None, and that a completed one is left out.
    """
    submission_store, _, submission_registry = build_submission_registry(
        config=config_sub_fixture, event_fixture=file_system_event_fixture
    )
    header = models.SubmissionHeader(title="test")
    content = VALID_MINIMAL_METADATA_WITH_STUDY_EXAMPLES[0]

    reserved_id, reserved_pid = submission_registry.reserve_study_pid(header=header)
    empty_id = submission_registry.init_submission(header=header)
    stopped_id = submission_registry.init_submission(header=header)
    submission_registry.upsert_submission_content(
        submission_id=stopped_id, content=content
    )
    completed_id = submission_registry.init_submission(header=header)
    submission_registry.upsert_submission_content(
        submission_id=completed_id, content=content
    )
    submission_registry.complete_submission(id_=completed_id)
    stopped_pid = submission_store.get_by_id(stopped_id).accession_map["studies"][
        "test_study"
    ]

    observed = {
        submission.id: study_pid
        for submission, study_pid in submission_registry.get_pending_submissions()
    }

    assert observed == {
        reserved_id: reserved_pid,
        empty_id: None,
        stopped_id: stopped_pid,
    }


def test_update_submission_header(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test that the header of a pending submission can be replaced, and that of a
    completed one cannot.
    """
    submission_store, _, submission_registry = build_submission_registry(
        config=config_sub_fixture, event_fixture=file_system_event_fixture
    )
    submission_id = submission_registry.init_submission(
        header=models.SubmissionHeader(title="old", description="old")
    )

    new_header = models.SubmissionHeader(title="new", description="new")
    submission_registry.update_submission_header(
        submission_id=submission_id, header=new_header
    )

    observed_submission = submission_store.get_by_id(submission_id)
    assert observed_submission.title == new_header.title
    assert observed_submission.description == new_header.description

    submission_registry.upsert_submission_content(
        submission_id=submission_id,
        content=VALID_MINIMAL_METADATA_WITH_STUDY_EXAMPLES[0],
    )
    submission_registry.complete_submission(id_=submission_id)
    completed_submission = submission_store.get_by_id(submission_id)

    with pytest.raises(SubmissionRegistry.StatusError):
        submission_registry.update_submission_header(
            submission_id=submission_id,
            header=models.SubmissionHeader(title="newer"),
        )

    assert submission_store.get_by_id(submission_id) == completed_submission
