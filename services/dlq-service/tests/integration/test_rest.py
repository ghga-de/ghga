# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Integration tests that focus on the REST API"""

from json import loads

import pytest

from tests.fixtures import utils
from tests.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio


async def test_get_event_success(joint_fixture: JointFixture, prepopped_events):
    """Test successful case of getting the next event(s) for a given service/topic"""
    stored = prepopped_events[utils.UFS][utils.USER_EVENTS]
    assert len(stored) > 0
    expected = [loads(event.model_dump_json()) for event in stored]

    response = await joint_fixture.rest_client.get(
        f"/{utils.UFS}/{utils.USER_EVENTS}", headers=utils.VALID_AUTH_HEADER
    )
    assert response.status_code == 200
    assert response.json() == expected
