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

from datetime import timedelta

from ghga_service_commons.utils.utc_dates import now_as_utc

from metldata.submission_registry.models import (
    StatusChange,
    Submission,
    SubmissionStatus,
)


def test_submission_current_status():
    """Test whether the current status property returns the latest status."""

    submission = Submission(
        title="test",
        description="test",
        content={"test_class": [{"alias": "test_alias1"}]},
        accession_map={"test_class": {"test_alias1": "test_accession1"}},
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
