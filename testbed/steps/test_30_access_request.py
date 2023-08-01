# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Step definitions for access request tests"""

from datetime import timedelta
from typing import Sequence

import httpx
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.providers.akafka.testutils import EventRecorder, RecordedEvent
from pytest_asyncio import fixture as async_fixture

from .conftest import (
    TIMEOUT,
    Config,
    JointFixture,
    LoginFixture,
    MongoFixture,
    given,
    parse,
    scenarios,
    then,
    unset_state,
    when,
)

scenarios("../features/30_access_request.feature")


@async_fixture
async def event_recorder(fixtures: JointFixture) -> EventRecorder:
    event_recorder = fixtures.kafka.record_events(in_topic="notifications")
    await event_recorder.start_recording()
    return event_recorder


@async_fixture
async def recorded_events(event_recorder: EventRecorder) -> Sequence[RecordedEvent]:
    try:
        await event_recorder.stop_recording()
    except event_recorder.stop_recording:
        pass
    return event_recorder.recorded_events


@given("no access requests have been made yet")
def ars_database_is_empty(config: Config, mongo: MongoFixture):
    mongo.empty_databases(config.ars_db_name)
    unset_state("is allowed to download", mongo)


@given("the claims repository is empty")
def claims_repository_is_empty(config: Config, mongo: MongoFixture):
    mongo.empty_databases(config.auth_db_name)


@when("I request access to the test dataset", target_fixture="response")
def request_access_for_dataset(config: Config, login: LoginFixture, event_recorder):
    assert event_recorder
    url = f"{config.ars_url}/access-requests"
    date_now = now_as_utc()
    user, headers = login
    data = {
        "user_id": user["_id"],
        "dataset_id": "dataset-1",
        "email": user["email"],
        "request_text": "Can I access the test dataset?",
        "access_starts": date_now.isoformat(),
        "access_ends": (date_now + timedelta(days=365)).isoformat(),
    }
    response = httpx.post(url, headers=headers, json=data)
    return response


@then(parse('an email has been sent to "{email}"'))
def check_email_sent_to(email: str, recorded_events: Sequence[RecordedEvent]):
    assert any(
        event.payload["recipient_email"] == email
        for event in recorded_events
        if event.type_ == "notification"
    )


@when("I fetch the list of access requests", target_fixture="response")
def fetch_list_of_access_requests(config: Config, login: LoginFixture):
    url = f"{config.ars_url}/access-requests"
    response = httpx.get(url, headers=login.headers, timeout=TIMEOUT)
    return response


@then(parse('there is one request for the test dataset from "{name}"'))
def there_is_one_request(name: str, response: httpx.Response):
    requests = response.json()
    requests = [
        request
        for request in requests
        if request["dataset_id"] == "dataset-1" and request["full_user_name"] == name
    ]
    assert len(requests) == 1


@when(parse('I allow the pending request from "{name}"'), target_fixture="response")
def allow_pending_request(
    config: Config, name: str, login: LoginFixture, response: httpx.Response
):
    requests = response.json()
    requests = [
        request
        for request in requests
        if request["dataset_id"] == "dataset-1"
        and request["status"] == "pending"
        and request["full_user_name"] == name
    ]
    assert len(requests) == 1
    request = requests[0]
    request_id = request["id"]
    url = f"{config.ars_url}/access-requests/{request_id}"
    data = {"status": "allowed"}
    response = httpx.patch(url, headers=login.headers, json=data)
    return response


@then(parse('the status of the request from "{name}" is "{status}"'))
def there_are_access_requests(name: str, status: str, response: httpx.Response):
    requests = response.json()
    requests = [
        request
        for request in requests
        if request["dataset_id"] == "dataset-1" and request["full_user_name"] == name
    ]
    assert len(requests) == 1
    request = requests[0]
    assert request["status"] == status
