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

from ghga_service_chassis_lib.utils import now_as_utc

from metldata.config import Config
from metldata.submission_registry import models
from metldata.submission_registry.event_publisher import EventPublisher

from .fixtures.config import config_fixture  # noqa:402
from .fixtures.utils import check_source_event


def test_happy(config_fixture: Config):  # noqa: F811
    """Test the happy path of publishing a submission."""

    event_publisher = EventPublisher(config=config_fixture)

    # publish a submission:
    submission = models.Submission(
        id="submission001",
        title="test",
        description="test",
        content={"test": "test"},
        status_history=[
            models.StatusChange(
                timestamp=now_as_utc(), new_status=models.SubmissionStatus.PENDING
            )
        ],
    )
    event_publisher.publish_submission(submission)

    # check published source event:
    check_source_event(
        expected_content=submission,
        source_events_dir=config_fixture.source_events_dir,
    )
