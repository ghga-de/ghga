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

"""Utils for Fixture handling"""

import json
from pathlib import Path

from metldata.submission_registry import models
from metldata.submission_registry.event_publisher import get_source_event_path

BASE_DIR = Path(__file__).parent.resolve()


def does_event_exist(*, submission_id: str, source_events_dir: Path) -> bool:
    """Checks whether an event for the submission with the specified ID exists."""

    json_path = get_source_event_path(
        submission_id=submission_id, source_events_dir=source_events_dir
    )
    return json_path.exists()


def check_source_event(*, expected_content: models.Submission, source_events_dir: Path):
    """Check the content of a source event.

    Raises:
        AssertionError: if it does not match the expectations.
        EventNotPublishedError: if the event was not yet published.
    """

    assert does_event_exist(
        submission_id=expected_content.id, source_events_dir=source_events_dir
    )

    json_path = get_source_event_path(
        submission_id=expected_content.id, source_events_dir=source_events_dir
    )

    with open(json_path, "r", encoding="utf-8") as file:
        published_event = json.load(file)
    assert expected_content == models.Submission(**published_event)
