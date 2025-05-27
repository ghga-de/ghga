# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from hexkit.providers.mongodb.testutils import MongoDbFixture
from pytest_httpx import HTTPXMock

from tests.fixtures import RestFixture

pytestmark = pytest.mark.asyncio()

DATE_NOW = now_as_utc()
ONE_YEAR = timedelta(days=365)
DATASET_TITLE = "A Great Dataset"
DATASET_DESCRIPTION = "This is a description of A Great Dataset"
DAC_ALIAS = "Some DAC"
DAC_EMAIL = "dac@some.org"

CREATION_DATA = {
    "user_id": "id-of-john-doe@ghga.de",
    "dataset_id": "DS001",
    "iva_id": "some-iva",
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


def norm_utc(date: str) -> str:
    """Replace Z with +00:00 in the given date string."""
    return date[:-1] + "+00:00" if date.endswith("Z") else date


def assert_same_datetime(date1: str, date2: str, max_diff_seconds=5) -> None:
    """Assert that the two given dates in iso format are very close."""
    assert (
        abs(iso2timestamp(norm_utc(date2)) - iso2timestamp(norm_utc(date1)))
        < max_diff_seconds
    )


@pytest.fixture(name="use_test_dataset", autouse=True)
def test_dataset_fixture(config, mongodb: MongoDbFixture):
    """Populate the DB with a test dataset"""
    mongodb.client[config.db_name]["datasets"].insert_one(
        {
            "_id": "DS001",
            "title": DATASET_TITLE,
            "description": DATASET_DESCRIPTION,
            "dac_alias": DAC_ALIAS,
            "dac_email": DAC_EMAIL,
        }
    )


async def test_health_check(rest: RestFixture):
    """Test that the health check endpoint works."""
    response = await rest.rest_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


async def test_create_access_request(
    rest: RestFixture, auth_headers_doe: dict[str, str]
):
    """Test that an active user can create an access request."""
    kafka = rest.kafka
    topic = rest.config.access_request_topic
    async with kafka.record_events(in_topic=topic) as recorder:
        response = await rest.rest_client.post(
            "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
        )

    assert response.status_code == 201
    access_request_id = response.json()
    assert_is_uuid(access_request_id)

    # check that an event was published for 'access request created'
    assert len(recorder.recorded_events) == 1
    recorded_event = recorder.recorded_events[0]
    assert recorded_event.key == access_request_id

    for key in ["user_id", "dataset_id", "request_text", "access_ends"]:
        assert recorded_event.payload[key] == CREATION_DATA[key]

    assert recorded_event.payload["status"] == "pending"
    assert recorded_event.payload["dataset_title"] == DATASET_TITLE
    assert recorded_event.payload["dataset_description"] == DATASET_DESCRIPTION
    assert recorded_event.payload["dac_alias"] == DAC_ALIAS
    assert recorded_event.payload["dac_email"] == DAC_EMAIL
    assert recorded_event.type_ == "upserted"


async def test_create_access_request_unauthorized(
    rest: RestFixture, auth_headers_doe: dict[str, str]
):
    """Test that creating an access request needs authorization."""
    client = rest.rest_client
    # test without authentication
    response = await client.post("/access-requests", json=CREATION_DATA)
    assert response.status_code == 403

    # test creating an access request for another user
    response = await client.post(
        "/access-requests",
        json={**CREATION_DATA, "user_id": "some-other-user@ghga.de"},
        headers=auth_headers_doe,
    )
    assert response.status_code == 403


async def test_create_access_request_that_is_too_long(
    rest: RestFixture, auth_headers_doe: dict[str, str]
):
    """Test that an access request that is too long cannot be created."""
    response = await rest.rest_client.post(
        "/access-requests",
        json={
            **CREATION_DATA,
            "access_ends": (DATE_NOW + 3 * ONE_YEAR).isoformat(),
        },
        headers=auth_headers_doe,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Access end date is invalid"


async def test_create_access_request_with_invalid_dataset_id(
    rest: RestFixture, auth_headers_doe: dict[str, str]
):
    """Test that an access request must have a valid dataset ID."""
    response = await rest.rest_client.post(
        "/access-requests",
        json={
            **CREATION_DATA,
            "dataset_id": "This is not a valid dataset ID!",
        },
        headers=auth_headers_doe,
    )
    assert response.status_code == 422
    msg = str(response.json()["detail"])
    assert "dataset_id" in msg
    assert "String should match pattern" in msg


async def test_create_access_request_with_nonexistent_dataset_id(
    rest: RestFixture, auth_headers_doe: dict[str, str]
):
    """Test that an access request must have a dataset ID which exists in the database."""
    response = await rest.rest_client.post(
        "/access-requests",
        json={
            **CREATION_DATA,
            "dataset_id": "DS404",
        },
        headers=auth_headers_doe,
    )
    assert response.status_code == 404
    msg = str(response.json()["detail"])
    assert msg == "Dataset not found"


async def test_get_access_requests(
    rest: RestFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
):
    """Test that users can get their access requests."""
    client = rest.rest_client
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
    assert request["iva_id"] == "some-iva"
    assert request["dataset_id"] == "DS001"
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
    assert request["dataset_id"] == "DS001"
    assert request["status"] == "pending"
    request = requests[1]
    assert request["id"] == access_request_id
    assert request["user_id"] == "id-of-john-doe@ghga.de"
    assert request["dataset_id"] == "DS001"
    assert request["status"] == "pending"


async def test_get_access_requests_unauthorized(rest: RestFixture):
    """Test that getting access requests needs authorization."""
    client = rest.rest_client
    # test unauthenticated
    response = await client.get("/access-requests")
    assert response.status_code == 403


async def test_filter_access_requests(
    rest: RestFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
):
    """Test that when getting access requests these can be filtered."""
    client = rest.rest_client
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
        "/access-requests?dataset_id=DS001", headers=auth_headers_doe
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await client.get(
        "/access-requests?dataset_id=DS002", headers=auth_headers_doe
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
        "user_id=id-of-john-doe@ghga.de&dataset_id=DS001&status=pending",
        headers=auth_headers_doe,
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_patch_access_request_status(
    rest: RestFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
    httpx_mock: HTTPXMock,
):
    """Test that data stewards can change the status of access requests."""
    # mock setting the access grant
    httpx_mock.add_response(
        method="POST",
        url="http://access/users/id-of-john-doe@ghga.de/ivas/some-iva/datasets/DS001",
        status_code=204,
    )

    client = rest.rest_client
    # create access request as user
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
    )
    assert response.status_code == 201
    access_request_id = response.json()
    assert_is_uuid(access_request_id)

    # set status to allowed as data steward
    kafka = rest.kafka
    topic = rest.config.access_request_topic
    async with kafka.record_events(in_topic=topic) as recorder:
        response = await rest.rest_client.patch(
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
    assert norm_utc(validity["valid_until"]) == CREATION_DATA["access_ends"]

    # check that an event was published for 'access request allowed'
    assert len(recorder.recorded_events) == 1
    recorded_event = recorder.recorded_events[0]
    assert recorded_event.key == access_request_id
    for key in ["user_id", "dataset_id", "request_text", "access_ends"]:
        assert recorded_event.payload[key] == CREATION_DATA[key]

    assert recorded_event.payload["status"] == "allowed"
    assert recorded_event.payload["dataset_title"] == DATASET_TITLE
    assert recorded_event.payload["dataset_description"] == DATASET_DESCRIPTION
    assert recorded_event.payload["dac_alias"] == DAC_ALIAS
    assert recorded_event.payload["dac_email"] == DAC_EMAIL
    assert recorded_event.type_ == "upserted"

    # get request as user
    response = await client.get("/access-requests", headers=auth_headers_doe)

    assert response.status_code == 200
    requests = response.json()

    assert isinstance(requests, list)
    assert len(requests) == 1
    request = requests[0]
    assert request["id"] == access_request_id
    assert request["user_id"] == "id-of-john-doe@ghga.de"
    assert request["iva_id"] == "some-iva"
    assert request["dataset_id"] == "DS001"
    assert request["status"] == "allowed"
    assert request["status_changed"]
    assert request["changed_by"] is None  # cannot see internals
    assert_same_datetime(request["access_starts"], CREATION_DATA["access_starts"], 300)
    assert norm_utc(request["access_ends"]) == CREATION_DATA["access_ends"]

    # get request as data steward
    response = await client.get("/access-requests", headers=auth_headers_steward)

    assert response.status_code == 200
    requests = response.json()

    assert isinstance(requests, list)
    assert len(requests) == 1
    request = requests[0]
    assert request["id"] == access_request_id
    assert request["user_id"] == "id-of-john-doe@ghga.de"
    assert request["iva_id"] == "some-iva"
    assert request["dataset_id"] == "DS001"
    assert request["status"] == "allowed"
    assert request["status_changed"]
    assert request["changed_by"] == "id-of-rod-steward@ghga.de"  # can see internals
    assert_same_datetime(request["access_starts"], CREATION_DATA["access_starts"], 300)
    assert norm_utc(request["access_ends"]) == CREATION_DATA["access_ends"]


async def test_patch_access_request_with_another_iva(
    rest: RestFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
    httpx_mock: HTTPXMock,
):
    """Test that data stewards can change the status and IVA of access requests."""
    # mock setting the access grant
    httpx_mock.add_response(
        method="POST",
        url="http://access/users/id-of-john-doe@ghga.de"
        "/ivas/another-iva/datasets/DS001",
        status_code=204,
    )

    client = rest.rest_client
    # create access request as user
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
    )
    assert response.status_code == 201
    access_request_id = response.json()
    assert_is_uuid(access_request_id)

    # set status to allowed as data steward
    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        json={"iva_id": "another-iva", "status": "allowed"},
        headers=auth_headers_steward,
    )
    assert response.status_code == 204

    # get request back as user
    response = await client.get("/access-requests", headers=auth_headers_doe)

    assert response.status_code == 200
    requests = response.json()

    assert isinstance(requests, list)
    assert len(requests) == 1
    request = requests[0]
    assert request["id"] == access_request_id
    assert request["user_id"] == "id-of-john-doe@ghga.de"
    # make sure that the IVA has been changed
    assert request["iva_id"] == "another-iva"
    assert request["dataset_id"] == "DS001"
    assert request["status"] == "allowed"
    assert request["status_changed"]
    assert request["changed_by"] is None


async def test_must_be_data_steward_to_patch_access_request(
    rest: RestFixture,
    auth_headers_doe: dict[str, str],
):
    """Test that only data stewards can change the status of access requests."""
    client = rest.rest_client
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
    rest: RestFixture,
    auth_headers_steward: dict[str, str],
):
    """Test that data stewards get an error when patching non-existing requests."""
    response = await rest.rest_client.patch(
        "/access-requests/some-non-existing-request",
        json={"status": "allowed"},
        headers=auth_headers_steward,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Access request not found"


async def test_patch_only_iva_id(
    rest: RestFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
):
    """Test that data stewards can change just the IVA ID of a request."""
    client = rest.rest_client
    # create access request as user
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
    )
    assert response.status_code == 201
    access_request_id = response.json()
    assert_is_uuid(access_request_id)

    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        # note: the data steward is not bound to the date restrictions
        json={"iva_id": "another-iva"},
        headers=auth_headers_steward,
    )
    assert response.status_code == 204

    # get request back as user
    response = await client.get("/access-requests", headers=auth_headers_doe)

    assert response.status_code == 200
    requests = response.json()
    assert isinstance(requests, list)
    assert len(requests) == 1
    request = requests[0]

    # make sure that only the IVA ID has been changed
    assert request["id"] == access_request_id
    assert request["user_id"] == "id-of-john-doe@ghga.de"
    assert request["iva_id"] == "another-iva"
    assert request["status"] == "pending"
    assert request["status_changed"] is None
    assert request["changed_by"] is None
    assert_same_datetime(request["access_starts"], CREATION_DATA["access_starts"], 300)
    assert norm_utc(request["access_ends"]) == CREATION_DATA["access_ends"]


async def test_patch_only_access_duration(
    rest: RestFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
):
    """Test that data stewards can change just the access duration of a request."""
    client = rest.rest_client
    # create access request as user
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
    )
    assert response.status_code == 201
    access_request_id = response.json()
    assert_is_uuid(access_request_id)

    access_starts = (DATE_NOW + ONE_YEAR).isoformat()
    access_ends = (DATE_NOW + 4 * ONE_YEAR).isoformat()

    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        # note: the data steward is not bound to the date restrictions
        json={
            "access_starts": access_starts,
            "access_ends": access_ends,
        },
        headers=auth_headers_steward,
    )
    assert response.status_code == 204

    # get request back as user
    response = await client.get("/access-requests", headers=auth_headers_doe)

    assert response.status_code == 200
    requests = response.json()
    assert isinstance(requests, list)
    assert len(requests) == 1
    request = requests[0]

    # make sure that only the access duration has been changed
    assert request["id"] == access_request_id
    assert request["user_id"] == "id-of-john-doe@ghga.de"
    assert request["iva_id"] == "some-iva"
    assert request["status"] == "pending"
    assert request["status_changed"] is None
    assert request["changed_by"] is None
    assert norm_utc(request["access_starts"]) == access_starts
    assert norm_utc(request["access_ends"]) == access_ends


async def test_patch_invalid_access_duration(
    rest: RestFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
):
    """Test that data stewards get an error when providing an invalid duration."""
    client = rest.rest_client
    # create access request as user
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
    )
    assert response.status_code == 201
    access_request_id = response.json()
    assert_is_uuid(access_request_id)

    expected_message = "Access end date must be later than access start date"

    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        json={"access_ends": CREATION_DATA["access_starts"]},
        headers=auth_headers_steward,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == expected_message

    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        json={"access_ends": CREATION_DATA["access_starts"]},
        headers=auth_headers_steward,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == expected_message

    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        json={
            "access_starts": CREATION_DATA["access_ends"],
            "access_ends": CREATION_DATA["access_starts"],
        },
        headers=auth_headers_steward,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == expected_message


async def test_patch_access_duration_for_allowed_request(
    rest: RestFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
    httpx_mock: HTTPXMock,
):
    """Test that data stewards cannot change the duration of an allowed request."""
    # mock setting the access grant
    httpx_mock.add_response(
        method="POST",
        url="http://access/users/id-of-john-doe@ghga.de/ivas/some-iva/datasets/DS001",
        status_code=204,
    )

    client = rest.rest_client
    # create access request as user
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
    )
    assert response.status_code == 201
    access_request_id = response.json()
    assert_is_uuid(access_request_id)

    # set status to allowed as data steward
    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        json={"status": "allowed"},
        headers=auth_headers_steward,
    )
    assert response.status_code == 204

    # try to change the end date of the request
    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        json={"access_ends": (DATE_NOW + 2 * ONE_YEAR).isoformat()},
        headers=auth_headers_steward,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Access request has already been processed"


async def test_patch_state_change_of_denied_request(
    rest: RestFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
):
    """Test that data stewards cannot change the state of a denied request."""
    client = rest.rest_client
    # create access request as user
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
    )
    assert response.status_code == 201
    access_request_id = response.json()
    assert_is_uuid(access_request_id)

    # set status to allowed as data steward
    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        json={"status": "denied"},
        headers=auth_headers_steward,
    )
    assert response.status_code == 204

    # try to change the state of the request
    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        json={"status": "pending"},
        headers=auth_headers_steward,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Access request has already been processed"
    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        json={"status": "allowed"},
        headers=auth_headers_steward,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Access request has already been processed"


async def test_patch_everything_when_allowing_request(
    rest: RestFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
    httpx_mock: HTTPXMock,
):
    """Test that data stewards can modify multiple fields when allowing a request."""
    # mock setting the access grant
    httpx_mock.add_response(
        method="POST",
        url="http://access/users/id-of-john-doe@ghga.de/ivas/new-iva/datasets/DS001",
        status_code=204,
    )

    client = rest.rest_client
    # create access request as user
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
    )
    assert response.status_code == 201
    access_request_id = response.json()
    assert_is_uuid(access_request_id)

    access_starts = (DATE_NOW + 2 * ONE_YEAR).isoformat()
    access_ends = (DATE_NOW + 3 * ONE_YEAR).isoformat()

    # set status to allowed and patch everything as data steward
    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        json={
            "status": "allowed",
            "iva_id": "new-iva",
            "access_starts": access_starts,
            "access_ends": access_ends,
            "ticket_id": "some-ticket-id",
            "internal_note": "Some internal note",
            "note_to_requester": "Some note to requester",
        },
        headers=auth_headers_steward,
    )
    assert response.status_code == 204

    # get request as data steward
    response = await client.get("/access-requests", headers=auth_headers_steward)

    assert response.status_code == 200
    requests = response.json()
    assert isinstance(requests, list)
    assert len(requests) == 1
    request = requests[0]

    # make sure that everything has been changed
    assert request["id"] == access_request_id
    assert request["user_id"] == "id-of-john-doe@ghga.de"
    assert request["iva_id"] == "new-iva"
    assert request["dataset_id"] == "DS001"
    assert request["status"] == "allowed"
    assert request["status_changed"]
    assert request["changed_by"] == "id-of-rod-steward@ghga.de"
    assert norm_utc(request["access_starts"]) == access_starts
    assert norm_utc(request["access_ends"]) == access_ends
    assert request["ticket_id"] == "some-ticket-id"
    assert request["internal_note"] == "Some internal note"
    assert request["note_to_requester"] == "Some note to requester"


async def test_patch_ticket_id_and_notes(
    rest: RestFixture,
    auth_headers_doe: dict[str, str],
    auth_headers_steward: dict[str, str],
):
    """Test setting the ticket ID and notes of a pending request."""
    client = rest.rest_client
    # create access request as user
    response = await client.post(
        "/access-requests", json=CREATION_DATA, headers=auth_headers_doe
    )
    assert response.status_code == 201
    access_request_id = response.json()
    assert_is_uuid(access_request_id)

    # set ticket ID as data steward
    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        json={
            "ticket_id": "some-ticket-id",
        },
        headers=auth_headers_steward,
    )
    assert response.status_code == 204

    # get request as data steward
    response = await client.get("/access-requests", headers=auth_headers_steward)

    assert response.status_code == 200
    requests = response.json()
    assert isinstance(requests, list)
    assert len(requests) == 1
    request = requests[0]

    # make sure that the ticket ID has been set
    assert request["id"] == access_request_id
    assert request["ticket_id"] == "some-ticket-id"
    assert request["internal_note"] is None
    assert request["note_to_requester"] is None
    assert request["status"] == "pending"
    assert not request["status_changed"]

    # set notes as data steward
    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        json={
            "internal_note": "Some internal note",
            "note_to_requester": "Some note to requester",
        },
        headers=auth_headers_steward,
    )
    assert response.status_code == 204

    # get request as data steward
    response = await client.get("/access-requests", headers=auth_headers_steward)

    assert response.status_code == 200
    requests = response.json()
    assert isinstance(requests, list)
    assert len(requests) == 1
    request = requests[0]

    # make sure that notes have been set
    assert request["id"] == access_request_id
    assert request["ticket_id"] == "some-ticket-id"
    assert request["internal_note"] == "Some internal note"
    assert request["note_to_requester"] == "Some note to requester"
    assert request["status"] == "pending"
    assert not request["status_changed"]

    # reset ticket ID and notes as data steward
    response = await rest.rest_client.patch(
        f"/access-requests/{access_request_id}",
        json={
            "ticket_id": "",
            "internal_note": "",
            "note_to_requester": "",
        },
        headers=auth_headers_steward,
    )
    assert response.status_code == 204

    # get request as data steward
    response = await client.get("/access-requests", headers=auth_headers_steward)

    assert response.status_code == 200
    requests = response.json()
    assert isinstance(requests, list)
    assert len(requests) == 1
    request = requests[0]

    # make sure that everything has been changed
    assert request["id"] == access_request_id
    assert request["ticket_id"] is None
    assert request["internal_note"] is None
    assert request["note_to_requester"] is None
    assert request["status"] == "pending"
    assert not request["status_changed"]
