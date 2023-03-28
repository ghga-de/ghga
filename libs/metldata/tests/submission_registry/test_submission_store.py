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

"""Testing the submission store."""

import pytest

from metldata.config import Config
from metldata.submission_registry import models
from metldata.submission_registry.submission_store import SubmissionStore
from tests.fixtures.config import config_fixture  # noqa: F401

EXAMPLE_SUBMISSION = models.SubmissionCreation(
    title="test submission", content={"test": "test"}
)


def test_happy(config_fixture: Config):  # noqa: F811
    """Test the happy path of inserting, querying, and updating a submission using
    the submission store."""

    submission_store = SubmissionStore(config=config_fixture)

    # create new submission:
    submission_created = submission_store.insert_new(submission=EXAMPLE_SUBMISSION)

    # query newly created submission:
    submission_queried = submission_store.get_by_id(submission_id=submission_created.id)
    assert submission_created == submission_queried

    # update the submision:
    submission_updated = submission_created.copy(
        update={"title": "updated test submission"}
    )
    submission_store.update_existing(submission=submission_updated)

    # query updated submission:
    submission_updated_queried = submission_store.get_by_id(
        submission_id=submission_updated.id
    )
    assert submission_updated_queried == submission_updated


def test_query_non_existing(config_fixture: Config):  # noqa: F811
    """Test querying for a non-existing submission."""

    submission_store = SubmissionStore(config=config_fixture)

    with pytest.raises(SubmissionStore.SubmissionDoesNotExistError):
        _ = submission_store.get_by_id(submission_id="non-exisitng-id")
