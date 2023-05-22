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

"""Test model functionality."""

from contextlib import nullcontext
from datetime import timedelta

import pytest
from ghga_service_commons.utils.utc_dates import now_as_utc
from pydantic import ValidationError

from metldata.submission_registry.models import (
    AccessionMap,
    StatusChange,
    Submission,
    SubmissionStatus,
)


def test_submission_current_status():
    """Test whether the current status property returns the latest status."""

    submission = Submission(
        title="test",
        description="test",
        content={"test_class": {"test_alias1": "test"}},
        accession_map={"test_class": {"test_alias1": "test_id1"}},
        id="testsubmission001",
        status_history=(
            StatusChange(
                timestamp=now_as_utc(), new_status=SubmissionStatus.IN_REVIEW  # second
            ),
            StatusChange(
                timestamp=now_as_utc() + timedelta(days=10),  # third
                new_status=SubmissionStatus.COMPLETED,
            ),
            StatusChange(
                timestamp=now_as_utc() - timedelta(days=10),  # first
                new_status=SubmissionStatus.PENDING,
            ),
        ),
    )

    assert submission.current_status == SubmissionStatus.COMPLETED


@pytest.mark.parametrize(
    "accession_map, is_valid",
    [
        (
            {
                "test_class1": {"test_alias1": "test_id1"},
                "test_class2": {"test_alias2": "test_id2", "test_alias3": "test_id3"},
            },
            True,
        ),
        # missing class in accession map:
        (
            {
                "test_class1": {"test_alias1": "test_id1"},
            },
            False,
        ),
        # additional class in accession map:
        (
            {
                "test_class1": {"test_alias1": "test_id1"},
                "test_class2": {"test_alias2": "test_id2", "test_alias3": "test_id3"},
                "test_class3": {"test_alias4": "test_id4"},
            },
            False,
        ),
        # missing resource in access map:
        (
            {
                "test_class1": {"test_alias1": "test_id1"},
                "test_class2": {"test_alias2": "test_id2"},
            },
            False,
        ),
        # additional resource in access map:
        (
            {
                "test_class1": {"test_alias1": "test_id1"},
                "test_class2": {
                    "test_alias2": "test_id2",
                    "test_alias3": "test_id3",
                    "test_alias4": "test_id4",
                },
            },
            False,
        ),
        # re-use of accessions accross classes:
        (
            {
                "test_class1": {"test_alias1": "test_id1"},
                "test_class2": {"test_alias2": "test_id1", "test_alias3": "test_id2"},
            },
            False,
        ),
    ],
)
def test_submission_accession_map_validation(
    accession_map: AccessionMap, is_valid: bool
):
    """Tests validation of the accession map."""

    with nullcontext() if is_valid else pytest.raises(ValidationError):  # type: ignore
        Submission(
            title="test",
            description="test",
            content={
                "test_class1": {"test_alias1": "test"},
                "test_class2": {"test_alias2": "test", "test_alias3": "test"},
            },
            accession_map=accession_map,
            id="testsubmission001",
            status_history=(
                StatusChange(
                    timestamp=now_as_utc(),
                    new_status=SubmissionStatus.COMPLETED,
                ),
            ),
        )
