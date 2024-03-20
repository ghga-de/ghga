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

"""Integration test using the REST API of the access request service"""

import json
from datetime import datetime, timedelta

import pytest
from ghga_service_commons.utils.utc_dates import now_as_utc
from pytest_httpx import HTTPXMock

from tests.fixtures import (  # noqa: F401
    JointFixture,
    fixture_auth_headers_doe,
    fixture_auth_headers_doe_inactive,
    fixture_auth_headers_steward,
    fixture_auth_headers_steward_inactive,
)

pytestmark = pytest.mark.asyncio(scope="session")

DATE_NOW = now_as_utc()
ONE_YEAR = timedelta(days=365)

CREATION_DATA = {
    "user_id": "id-of-john-doe@ghga.de",
    "dataset_id": "some-dataset",
    "email": "me@john-doe.name",
    "request_text": "Can I access some dataset?",
    "access_starts": DATE_NOW.isoformat(),
    "access_ends": (DATE_NOW + ONE_YEAR).isoformat(),
}


def assert_is_uuid(value: str) -> None:
    """Assert that the given value is a UUID"""
    assert isinstance(value, str)
    assert value.isascii()
    assert len(value) == 36
    assert value.count("-") == 4


def iso2timestamp(iso_date: str) -> float:
    """Get timestamp from given date in iso format."""
    return datetime.fromisoformat(iso_date).timestamp()


def assert_same_datetime(date1: str, date2: str, max_diff_seconds=5) -> None:
    """Assert that the two given dates in iso format are very close."""
    assert (
        abs(
            iso2timestamp(date2.replace("Z", "+00:00"))
            - iso2timestamp(date1.replace("Z", "+00:00"))
        )
        < max_diff_seconds
    )


async def test_health_check(joint_fixture: JointFixture):
    """Test that the health check endpoint works."""
    response = await joint_fixture.rest_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


async def test_create_access_request(
    joint_fixture: JointFixture, auth_headers_doe: dict[str, str]
):
    """Test that an active user can create an access request."""
    kafka = joint_fixture.kafka
    topic = joint_fixture.config.access_request_events_topic
    async with kafka.record_events(in_topic=topic):
        pass  # skip previous events
    async with kafka.record_events(in_topic=topic) as recorder:
        response = await joint_fixture.rest_client.post(
            "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
        )

    assert response.status_code == 201

    access_request_id = response.json()
    assert_is_uuid(access_request_id)

    # check that an event was published for 'access request created'
    assert len(recorder.recorded_events) == 1
    recorded_event = recorder.recorded_events[0]
    assert recorded_event.key == CREATION_DATA["user_id"]
    assert recorded_event.payload == {
        "user_id": CREATION_DATA["user_id"],
        "dataset_id": CREATION_DATA["dataset_id"],
    }
    assert (
        recorded_event.type_ == joint_fixture.config.access_request_created_event_type
    )


async def test_create_access_request_unauthorized(
    joint_fixture: JointFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_doe_inactive: dict[str, str],
):
    """Test that creating an access request needs authorization."""
    client = joint_fixture.rest_client
    # test without authentication
    response = await client.post("/access-requests", json=CREATION_DATA)
    assert response.status_code == 403

    # test with inactive user
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe_inactive
    )
    assert response.status_code == 403

    # test creating an access request for another user
    response = await client.post(
        "/access-requests",
        json={**CREATION_DATA, "user_id": "some-other-user@ghga.de"},
        headers=auth_headers_doe,
    )
    assert response.status_code == 403


async def test_create_access_request_that_is_too_long(
    joint_fixture: JointFixture, auth_headers_doe: dict[str, str]
):
    """Test that an access request that is too long cannot be created."""
    response = await joint_fixture.rest_client.post(
        "/access-requests",
        json={
            **CREATION_DATA,
            "access_ends": (DATE_NOW + 3 * ONE_YEAR).isoformat(),
        },
        headers=auth_headers_doe,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Access end date is invalid"


async def test_get_access_requests(
    joint_fixture: JointFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
):
    """Test that users can get their access requests."""
    client = joint_fixture.rest_client
    # create two access requests for different users
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
    )
    assert response.status_code == 201
    access_request_id = response.json()
    assert_is_uuid(access_request_id)
    response = await client.post(
        "/access-requests",
        json={**CREATION_DATA, "user_id": "id-of-rod-steward@ghga.de"},
        headers=auth_headers_steward,
    )
    assert response.status_code == 201
    another_access_request_id = response.json()
    assert_is_uuid(another_access_request_id)
    assert another_access_request_id != access_request_id

    # get own requests as user
    response = await client.get("/access-requests", headers=auth_headers_doe)

    assert response.status_code == 200
    requests = response.json()

    assert isinstance(requests, list)
    assert len(requests) == 1
    request = requests[0]
    assert request["id"] == access_request_id
    assert request["user_id"] == "id-of-john-doe@ghga.de"
    assert request["dataset_id"] == "some-dataset"
    assert request["status"] == "pending"

    # get all requests as data steward
    response = await client.get("/access-requests", headers=auth_headers_steward)

    assert response.status_code == 200
    requests = response.json()

    assert isinstance(requests, list)
    assert len(requests) == 2
    request = requests[0]
    # last made request comes first
    assert request["id"] == another_access_request_id
    assert request["user_id"] == "id-of-rod-steward@ghga.de"
    assert request["dataset_id"] == "some-dataset"
    assert request["status"] == "pending"
    request = requests[1]
    assert request["id"] == access_request_id
    assert request["user_id"] == "id-of-john-doe@ghga.de"
    assert request["dataset_id"] == "some-dataset"
    assert request["status"] == "pending"


async def test_get_access_requests_unauthorized(
    joint_fixture: JointFixture, auth_headers_doe_inactive: dict[str, str]
):
    """Test that getting access requests needs authorization."""
    client = joint_fixture.rest_client
    # test unauthenticated
    response = await client.get("/access-requests")
    assert response.status_code == 403

    # test with inactive user
    response = await client.get("/access-requests", headers=auth_headers_doe_inactive)
    assert response.status_code == 403


async def test_filter_access_requests(
    joint_fixture: JointFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
):
    """Test that when getting access requests these can be filtered."""
    client = joint_fixture.rest_client
    # create an access request
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
    )
    assert response.status_code == 201

    # without filter
    response = await client.get("/access-requests", headers=auth_headers_doe)
    assert response.status_code == 200
    assert len(response.json()) == 1

    # various filters
    response = await client.get(
        "/access-requests?user_id=id-of-john-doe@ghga.de", headers=auth_headers_doe
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await client.get(
        "/access-requests?user_id=somebody-else@ghga.de", headers=auth_headers_doe
    )
    assert response.status_code == 403  # only data steward can filter for other users

    response = await client.get(
        "/access-requests?user_id=somebody-else@ghga.de", headers=auth_headers_steward
    )
    assert response.status_code == 200
    assert len(response.json()) == 0

    response = await client.get(
        "/access-requests?dataset_id=some-dataset", headers=auth_headers_doe
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await client.get(
        "/access-requests?dataset_id=another-dataset", headers=auth_headers_doe
    )
    assert response.status_code == 200
    assert len(response.json()) == 0

    response = await client.get(
        "/access-requests?status=pending", headers=auth_headers_doe
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await client.get(
        "/access-requests?status=allowed", headers=auth_headers_doe
    )
    assert response.status_code == 200
    assert len(response.json()) == 0

    # combined filter
    response = await client.get(
        "/access-requests?"
        "user_id=id-of-john-doe@ghga.de&dataset_id=some-dataset&status=pending",
        headers=auth_headers_doe,
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_patch_access_request(
    joint_fixture: JointFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
    httpx_mock: HTTPXMock,
):
    """Test that data stewards can change the status of access requests."""
    # mock setting the the access grant
    httpx_mock.add_response(
        method="POST",
        url="http://access/users/id-of-john-doe@ghga.de/datasets/some-dataset",
        status_code=204,
    )

    client = joint_fixture.rest_client
    # create access request as user
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
    )
    assert response.status_code == 201
    access_request_id = response.json()
    assert_is_uuid(access_request_id)

    # set status to allowed as data steward
    kafka = joint_fixture.kafka
    topic = joint_fixture.config.access_request_events_topic
    async with kafka.record_events(in_topic=topic):
        pass  # skip previous events
    async with kafka.record_events(in_topic=topic) as recorder:
        response = await joint_fixture.rest_client.patch(
            f"/access-requests/{access_request_id}",
            json={"status": "allowed"},
            headers=auth_headers_steward,
        )
        assert response.status_code == 204

    # check that access has been granted
    grant_request = httpx_mock.get_request()
    assert grant_request
    validity = json.loads(grant_request.content)
    # validity period may start a bit later because integration tests can be slow
    assert_same_datetime(validity["valid_from"], CREATION_DATA["access_starts"], 300)
    assert (
        validity["valid_until"].replace("Z", "+00:00") == CREATION_DATA["access_ends"]
    )

    # check that an event was published for 'access request allowed'
    assert len(recorder.recorded_events) == 1
    recorded_event = recorder.recorded_events[0]
    assert recorded_event.key == CREATION_DATA["user_id"]
    assert recorded_event.payload == {
        "user_id": CREATION_DATA["user_id"],
        "dataset_id": CREATION_DATA["dataset_id"],
    }
    assert (
        recorded_event.type_ == joint_fixture.config.access_request_allowed_event_type
    )

    # get request as user
    response = await client.get("/access-requests", headers=auth_headers_doe)

    assert response.status_code == 200
    requests = response.json()

    assert isinstance(requests, list)
    assert len(requests) == 1
    request = requests[0]
    assert request["id"] == access_request_id
    assert request["user_id"] == "id-of-john-doe@ghga.de"
    assert request["dataset_id"] == "some-dataset"
    assert request["status"] == "allowed"
    assert request["status_changed"]
    assert request["changed_by"] is None  # cannot see internals

    # get request as data steward
    response = await client.get("/access-requests", headers=auth_headers_steward)

    assert response.status_code == 200
    requests = response.json()

    assert isinstance(requests, list)
    assert len(requests) == 1
    request = requests[0]
    assert request["id"] == access_request_id
    assert request["user_id"] == "id-of-john-doe@ghga.de"
    assert request["dataset_id"] == "some-dataset"
    assert request["status"] == "allowed"
    assert request["status_changed"]
    assert request["changed_by"] == "id-of-rod-steward@ghga.de"  # can see internals


async def test_must_be_data_steward_to_patch_access_request(
    joint_fixture: JointFixture,
    auth_headers_doe: dict[str, str],
):
    """Test that only data stewards can change the status of access requests."""
    client = joint_fixture.rest_client
    # create access request as user
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
    )
    assert response.status_code == 201
    access_request_id = response.json()
    assert_is_uuid(access_request_id)

    # set status without authentication
    response = await client.patch(
        f"/access-requests/{access_request_id}",
        json={"status": "allowed"},
    )
    assert response.status_code == 403
    # set status to allowed as the same user
    response = await client.patch(
        f"/access-requests/{access_request_id}",
        json={"status": "allowed"},
        headers=auth_headers_doe,
    )
    assert response.status_code == 403


async def test_patch_non_existing_access_request(
    joint_fixture: JointFixture,
    auth_headers_steward: dict[str, str],
):
    """Test that data stewards get an error when patching non-existing requests."""
    response = await joint_fixture.rest_client.patch(
        "/access-requests/some-non-existing-request",
        json={"status": "allowed"},
        headers=auth_headers_steward,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Access request not found"
