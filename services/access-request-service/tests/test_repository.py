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
#

"""Test the access request repository"""

from collections.abc import AsyncIterator, Mapping
from datetime import timedelta
from operator import attrgetter
from typing import Any, NamedTuple

import pytest
from ghga_service_commons.auth.ghga import AcademicTitle, AuthContext
from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc, utc_datetime

from ars.core.models import (
    AccessRequest,
    AccessRequestCreationData,
    AccessRequestData,
    AccessRequestStatus,
)
from ars.core.repository import AccessRequestConfig, AccessRequestRepository
from ars.ports.outbound.access_grants import AccessGrantsPort
from ars.ports.outbound.dao import AccessRequestDaoPort, ResourceNotFoundError
from ars.ports.outbound.event_pub import EventPublisherPort

pytestmark = pytest.mark.asyncio()

ONE_HOUR = timedelta(seconds=60 * 60)
ONE_YEAR = timedelta(days=365)

IAT = now_as_utc()
EXP = IAT + ONE_HOUR

auth_context_doe = AuthContext(
    id="id-of-john-doe@ghga.de",
    name="John Doe",
    email="john@home.org",
    title=AcademicTitle.DR,
    role=None,
    iat=IAT,
    exp=EXP,
)


auth_context_steward = AuthContext(
    id="id-of-rod-steward@ghga.de",
    name="Rod Steward",
    email="steward@ghga.de",
    title=None,
    role="data_steward@ghga.de",
    iat=IAT,
    exp=EXP,
)


config = AccessRequestConfig(
    access_upfront_max_days=365,
    access_grant_min_days=30,
    access_grant_max_days=2 * 365,
)


ACCESS_REQUESTS = [
    AccessRequest(
        id="request-id-1",
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS001",
        email="me@john-doe.name",
        request_text="Can I access some dataset?",
        access_starts=utc_datetime(2020, 1, 1, 0, 0),
        access_ends=utc_datetime(2020, 12, 31, 23, 59),
        full_user_name="Dr. John Doe",
        request_created=utc_datetime(2019, 12, 9, 12, 0),
        status=AccessRequestStatus.ALLOWED,
        status_changed=utc_datetime(2019, 12, 16, 12, 0),
        changed_by="id-of-rod-steward@ghga.de",
    ),
    AccessRequest(
        id="request-id-2",
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS002",
        email="me@john-doe.name",
        request_text="Can I access another dataset?",
        access_starts=utc_datetime(2020, 1, 1, 0, 0),
        access_ends=utc_datetime(2020, 12, 31, 23, 59),
        full_user_name="Dr. John Doe",
        request_created=utc_datetime(2019, 12, 9, 12, 0),
        status=AccessRequestStatus.ALLOWED,
        status_changed=utc_datetime(2019, 12, 16, 12, 0),
        changed_by="id-of-rod-steward@ghga.de",
    ),
    AccessRequest(
        id="request-id-3",
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS003",
        email="me@john-doe.name",
        request_text="Can I access yet another dataset?",
        access_starts=utc_datetime(2020, 1, 1, 0, 0),
        access_ends=utc_datetime(2020, 12, 31, 23, 59),
        full_user_name="Dr. John Doe",
        request_created=utc_datetime(2019, 12, 9, 12, 0),
        status=AccessRequestStatus.DENIED,
        status_changed=utc_datetime(2019, 12, 16, 12, 0),
        changed_by="id-of-rod-steward@ghga.de",
    ),
    AccessRequest(
        id="request-id-4",
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS007",
        email="me@john-doe.name",
        request_text="Can I access a new dataset?",
        access_starts=utc_datetime(2021, 1, 1, 0, 0),
        access_ends=utc_datetime(2021, 12, 31, 23, 59),
        full_user_name="Dr. John Doe",
        request_created=utc_datetime(2020, 12, 7, 12, 0),
        status=AccessRequestStatus.PENDING,
        status_changed=None,
        changed_by=None,
    ),
    AccessRequest(
        id="request-id-5",
        user_id="id-of-jane-roe@ghga.de",
        dataset_id="DS001",
        email="me@jane-roe.name",
        request_text="Can I access the same dataset as Joe?",
        access_starts=utc_datetime(2020, 1, 1, 0, 0),
        access_ends=utc_datetime(2020, 12, 31, 23, 59),
        full_user_name="Dr. Jane Roe",
        request_created=utc_datetime(2019, 12, 9, 12, 0),
        status=AccessRequestStatus.ALLOWED,
        status_changed=utc_datetime(2019, 12, 16, 12, 0),
        changed_by="id-of-rod-steward@ghga.de",
    ),
    AccessRequest(
        id="request-id-6",
        user_id="id-of-john-doe@ghga.de",
        iva_id="iva-of-john",
        dataset_id="DS003",
        email="me@john-doe.name",
        request_text="Can I access yet another dataset using this IVA?",
        access_starts=utc_datetime(2021, 6, 1, 0, 0),
        access_ends=utc_datetime(2021, 12, 31, 23, 59),
        full_user_name="Dr. John Doe",
        request_created=utc_datetime(2021, 5, 9, 12, 0),
        status=AccessRequestStatus.PENDING,
        status_changed=None,
        changed_by=None,
    ),
]


class AccessRequestDaoDummy(AccessRequestDaoPort):  # pyright: ignore
    """Dummy AccessRequest DAO for testing."""

    last_upsert: AccessRequest | None

    def reset(self):
        """Reset the last recorded upsert."""
        self.last_upsert = None

    def find_all(self, *, mapping: Mapping[str, Any]) -> AsyncIterator[AccessRequest]:
        """Find all records using a mapping."""

        async def async_iterator():
            for request in ACCESS_REQUESTS:
                if all(
                    value is None or value == getattr(request, key)
                    for key, value in mapping.items()
                ):
                    yield request

        return async_iterator()

    async def get_by_id(self, id_: str) -> AccessRequest:
        """Get a resource by providing its ID."""
        async for request in self.find_all(mapping={"id": id_}):
            return request
        raise ResourceNotFoundError(id_=id_)

    async def insert(self, dto: AccessRequestData) -> AccessRequest:
        """Create a new record."""
        self.last_upsert = AccessRequest(**dto.model_dump(), id="newly-created-id")
        return self.last_upsert

    async def update(self, dto: AccessRequest) -> None:
        """Update an existing resource."""
        self.last_upsert = dto


class MockAccessRequestEvent(NamedTuple):
    """Mock of AccessRequestDetails plus status field to represent event type"""

    user_id: str
    dataset_id: str
    status: str


class EventPublisherDummy(EventPublisherPort):
    """Dummy event publisher for testing."""

    events: list[MockAccessRequestEvent]

    def reset(self) -> None:
        """Reset the recorded events."""
        self.events = []

    @property
    def num_events(self):
        """Get total number of recorded events."""
        return len(self.events)

    def _record_request(self, *, request: AccessRequest, request_state: str):
        """Record a request as either created, allowed, or denied for a user and dataset."""
        mock_event = MockAccessRequestEvent(
            request.user_id, request.dataset_id, request_state
        )
        self.events.append(mock_event)

    async def publish_request_allowed(self, *, request: AccessRequest) -> None:
        """Mark an access request as allowed via event publish."""
        self._record_request(request=request, request_state="allowed")

    async def publish_request_created(self, *, request: AccessRequest) -> None:
        """Mark an access request as created via event publish."""
        self._record_request(request=request, request_state="created")

    async def publish_request_denied(self, *, request: AccessRequest) -> None:
        """Mark an access request as denied via event publish."""
        self._record_request(request=request, request_state="denied")


class AccessGrantsDummy(AccessGrantsPort):
    """Dummy adapter for granting download access."""

    last_grant: str
    simulate_error: bool

    def reset(self) -> None:
        """Reset the recorded grant."""
        self.last_grant = "nothing granted so far"
        self.simulate_error = False

    async def grant_download_access(
        self,
        user_id: str,
        iva_id: str,
        dataset_id: str,
        valid_from: UTCDatetime,
        valid_until: UTCDatetime,
    ) -> None:
        """Grant download access."""
        if self.simulate_error:
            self.last_grant = f"to {user_id} for {dataset_id} failed"
            raise self.AccessGrantsError
        self.last_grant = (
            f"to {user_id} with {iva_id}"
            f" for {dataset_id} from {valid_from} until {valid_until}"
        )


dao = AccessRequestDaoDummy()  # type: ignore
event_publisher = EventPublisherDummy()
access_grants = AccessGrantsDummy()


def reset():
    """Reset dummy adapters."""
    dao.reset()
    event_publisher.reset()
    access_grants.reset()


repository = AccessRequestRepository(
    config=config,
    access_request_dao=dao,
    event_publisher=event_publisher,
    access_grants=access_grants,
)


async def test_can_create_request():
    """Test that users can create an access request for themselves"""
    access_starts = now_as_utc()
    access_ends = access_starts + ONE_YEAR
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS001",
        email="me@john-doe.name",
        request_text="Can I access some dataset?",
        access_starts=access_starts,
        access_ends=access_ends,
    )
    reset()
    creation_date = now_as_utc()

    request = await repository.create(creation_data, auth_context=auth_context_doe)

    assert request.id == "newly-created-id"
    assert request.user_id == "id-of-john-doe@ghga.de"
    assert request.iva_id is None
    assert request.dataset_id == "DS001"
    assert request.email == "me@john-doe.name"
    assert request.request_text == "Can I access some dataset?"
    assert request.access_starts == request.request_created
    assert request.access_ends == creation_data.access_ends
    assert request.full_user_name == "Dr. John Doe"
    assert request.status == AccessRequestStatus.PENDING
    assert 0 <= (request.request_created - creation_date).seconds < 5
    assert request.status_changed is None
    assert request.changed_by is None

    assert dao.last_upsert == request

    # the 'publish_request_created' method should have been called, get events for request
    expected_event = MockAccessRequestEvent(
        request.user_id, request.dataset_id, "created"
    )
    assert event_publisher.events == [expected_event]

    assert access_grants.last_grant == "nothing granted so far"


async def test_can_create_request_with_an_iva():
    """Test that users can create an access request already specifying an IVA"""
    access_starts = now_as_utc()
    access_ends = access_starts + ONE_YEAR
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-doe@ghga.de",
        iva_id="some-iva_id",
        dataset_id="DS001",
        email="me@john-doe.name",
        request_text="Can I access some dataset?",
        access_starts=access_starts,
        access_ends=access_ends,
    )

    request = await repository.create(creation_data, auth_context=auth_context_doe)

    assert request.id == "newly-created-id"
    assert request.user_id == "id-of-john-doe@ghga.de"
    assert request.iva_id == "some-iva_id"
    assert request.dataset_id == "DS001"

    assert dao.last_upsert == request


async def test_cannot_create_request_for_somebody_else():
    """Test that users cannot create an access request for somebody else"""
    access_starts = now_as_utc()
    access_ends = access_starts + ONE_YEAR
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-foo@ghga.de",
        dataset_id="DS001",
        email="me@john-doe.name",
        request_text="Can I access some dataset?",
        access_starts=access_starts,
        access_ends=access_ends,
    )
    with pytest.raises(repository.AccessRequestError, match="Not authorized"):
        await repository.create(creation_data, auth_context=auth_context_doe)


async def test_silently_correct_request_that_is_too_early():
    """Test that requests that are too early are silently corrected"""
    creation_date = now_as_utc()
    access_starts = creation_date - 0.5 * ONE_YEAR
    access_ends = access_starts + 1.5 * ONE_YEAR
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS001",
        email="me@john-doe.name",
        request_text="Can I access some dataset?",
        access_starts=access_starts,
        access_ends=access_ends,
    )
    reset()

    request = await repository.create(creation_data, auth_context=auth_context_doe)

    assert 0 <= (request.request_created - creation_date).seconds < 5
    assert request.access_starts != creation_data.access_starts
    assert request.access_starts == request.request_created
    assert request.access_ends == creation_data.access_ends
    assert dao.last_upsert == request

    # There should be one event published which communicates the state of the request
    assert len(event_publisher.events) == 1


async def test_cannot_create_request_too_much_in_advance():
    """Test that users cannot create an access request too much in advance"""
    access_starts = now_as_utc() + 1.5 * ONE_YEAR
    access_ends = access_starts + ONE_YEAR
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS001",
        email="me@john-doe.name",
        request_text="Can I access some dataset?",
        access_starts=access_starts,
        access_ends=access_ends,
    )
    reset()

    with pytest.raises(
        repository.AccessRequestInvalidDuration, match="Access start date is invalid"
    ):
        await repository.create(creation_data, auth_context=auth_context_doe)

    assert dao.last_upsert is None
    assert event_publisher.num_events == 0


async def test_cannot_create_request_too_short():
    """Test that users cannot create an access request that is too short"""
    access_starts = now_as_utc()
    access_ends = access_starts + timedelta(days=29)
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS001",
        email="me@john-doe.name",
        request_text="Can I access some dataset?",
        access_starts=access_starts,
        access_ends=access_ends,
    )
    reset()

    with pytest.raises(
        repository.AccessRequestInvalidDuration, match="Access end date is invalid"
    ):
        await repository.create(creation_data, auth_context=auth_context_doe)

    assert dao.last_upsert is None
    assert event_publisher.num_events == 0


async def test_cannot_create_request_too_long():
    """Test that users cannot create an access request that is too long"""
    access_starts = now_as_utc()
    access_ends = access_starts + 2.5 * ONE_YEAR
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS001",
        email="me@john-doe.name",
        request_text="Can I access some dataset?",
        access_starts=access_starts,
        access_ends=access_ends,
    )
    reset()

    with pytest.raises(
        repository.AccessRequestInvalidDuration, match="Access end date is invalid"
    ):
        await repository.create(creation_data, auth_context=auth_context_doe)

    assert dao.last_upsert is None
    assert event_publisher.num_events == 0


async def test_can_get_all_requests_as_data_steward():
    """Test that a data steward can get all requests."""
    requests = await repository.get(auth_context=auth_context_steward)
    assert requests == sorted(
        ACCESS_REQUESTS, key=attrgetter("request_created"), reverse=True
    )


async def test_can_get_all_own_requests_as_requester():
    """Test that requesters can get their own requests."""
    requests = await repository.get(auth_context=auth_context_doe)
    assert 0 < len(requests) < len(ACCESS_REQUESTS)
    assert requests == sorted(
        (
            request.model_copy(update={"changed_by": None})  # data steward is hidden
            for request in ACCESS_REQUESTS
            if request.full_user_name == "Dr. John Doe"
        ),
        key=attrgetter("request_created"),
        reverse=True,
    )


async def test_users_cannot_get_requests_of_other_users():
    """Test that non data stewards cannot get requests of others."""
    with pytest.raises(repository.AccessRequestError, match="Not authorized"):
        await repository.get(
            auth_context=auth_context_doe, user_id="id-of-jane-roe@ghga.de"
        )


async def test_data_steward_can_get_requests_of_specific_user():
    """Test that data stewards can get requests of specific users."""
    requests = await repository.get(
        auth_context=auth_context_steward, user_id="id-of-jane-roe@ghga.de"
    )
    assert len(requests) == 1
    assert requests == [
        request
        for request in ACCESS_REQUESTS
        if request.full_user_name == "Dr. Jane Roe"
    ]


async def test_data_steward_can_get_requests_for_specific_dataset():
    """Test getting requests for a specific dataset."""
    requests = await repository.get(auth_context=auth_context_doe, dataset_id="DS002")
    assert len(requests) == 1
    assert requests == [
        request.model_copy(update={"changed_by": None})  # data steward is hidden
        for request in ACCESS_REQUESTS
        if request.dataset_id == "DS002"
    ]


async def test_data_steward_can_get_pending_requests():
    """Test getting only the pending requests."""
    requests = await repository.get(
        auth_context=auth_context_doe, status=AccessRequestStatus.PENDING
    )
    assert len(requests) == 2
    assert sorted(requests, key=lambda request: request.id) == [
        request
        for request in ACCESS_REQUESTS
        if request.status == AccessRequestStatus.PENDING
    ]


async def test_filtering_using_multiple_criteria():
    """Test filtering using multiple criteria at the same time."""
    requests = await repository.get(
        auth_context=auth_context_steward,
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS001",
        status=AccessRequestStatus.ALLOWED,
    )
    assert len(requests) == 1
    assert requests == [
        request
        for request in ACCESS_REQUESTS
        if request.user_id == "id-of-john-doe@ghga.de"
        and request.dataset_id == "DS001"
        and request.status == AccessRequestStatus.ALLOWED
    ]


async def test_set_status_to_allowed():
    """Test setting the status of a request from pending to allowed."""
    original_request = await dao.get_by_id("request-id-4")
    original_dict = original_request.model_dump()
    assert original_dict.pop("iva_id") is None
    assert original_dict.pop("status") == AccessRequestStatus.PENDING
    assert original_dict.pop("status_changed") is None
    assert original_dict.pop("changed_by") is None
    reset()

    await repository.update(
        "request-id-4",
        iva_id="some-iva",
        status=AccessRequestStatus.ALLOWED,
        auth_context=auth_context_steward,
    )

    changed_request = dao.last_upsert
    assert changed_request is not None
    changed_dict = changed_request.model_dump()
    assert changed_dict.pop("status") == AccessRequestStatus.ALLOWED
    assert changed_dict.pop("iva_id") == "some-iva"
    status_changed = changed_dict.pop("status_changed")
    assert status_changed is not None
    assert 0 <= (now_as_utc() - status_changed).seconds < 5
    assert changed_dict.pop("changed_by") == "id-of-rod-steward@ghga.de"
    assert changed_dict == original_dict

    expected_event = MockAccessRequestEvent(
        changed_request.user_id, changed_request.dataset_id, "allowed"
    )
    assert event_publisher.events == [expected_event]

    assert access_grants.last_grant == (
        "to id-of-john-doe@ghga.de with some-iva for DS007"
        " from 2021-01-01 00:00:00+00:00 until 2021-12-31 23:59:00+00:00"
    )


async def test_set_status_to_allowed_reusing_iva():
    """Test setting the status of a request to allowed reusing the IVA."""
    original_request = await dao.get_by_id("request-id-6")
    original_dict = original_request.model_dump()
    assert original_dict["iva_id"] == "iva-of-john"
    assert original_dict.pop("status") == AccessRequestStatus.PENDING
    assert original_dict.pop("status_changed") is None
    assert original_dict.pop("changed_by") is None
    reset()

    await repository.update(
        "request-id-6",
        status=AccessRequestStatus.ALLOWED,
        auth_context=auth_context_steward,
    )

    changed_request = dao.last_upsert
    assert changed_request is not None
    changed_dict = changed_request.model_dump()
    assert changed_dict.pop("status") == AccessRequestStatus.ALLOWED
    status_changed = changed_dict.pop("status_changed")
    assert status_changed is not None
    assert 0 <= (now_as_utc() - status_changed).seconds < 5
    assert changed_dict.pop("changed_by") == "id-of-rod-steward@ghga.de"
    assert changed_dict == original_dict

    expected_event = MockAccessRequestEvent(
        changed_request.user_id, changed_request.dataset_id, "allowed"
    )
    assert event_publisher.events == [expected_event]

    assert access_grants.last_grant == (
        "to id-of-john-doe@ghga.de with iva-of-john for DS003"
        " from 2021-06-01 00:00:00+00:00 until 2021-12-31 23:59:00+00:00"
    )


async def test_set_status_to_allowed_overriding_iva():
    """Test setting the status of a request to allowed overriding the IVA."""
    original_request = await dao.get_by_id("request-id-6")
    original_dict = original_request.model_dump()
    assert original_dict.pop("iva_id") == "iva-of-john"
    assert original_dict.pop("status") == AccessRequestStatus.PENDING
    assert original_dict.pop("status_changed") is None
    assert original_dict.pop("changed_by") is None
    reset()

    await repository.update(
        "request-id-6",
        iva_id="some-other-iva-of-john",
        status=AccessRequestStatus.ALLOWED,
        auth_context=auth_context_steward,
    )

    changed_request = dao.last_upsert
    assert changed_request is not None
    changed_dict = changed_request.model_dump()
    assert changed_dict.pop("iva_id") == "some-other-iva-of-john"
    assert changed_dict.pop("status") == AccessRequestStatus.ALLOWED
    status_changed = changed_dict.pop("status_changed")
    assert status_changed is not None
    assert 0 <= (now_as_utc() - status_changed).seconds < 5
    assert changed_dict.pop("changed_by") == "id-of-rod-steward@ghga.de"
    assert changed_dict == original_dict

    expected_event = MockAccessRequestEvent(
        changed_request.user_id, changed_request.dataset_id, "allowed"
    )
    assert event_publisher.events == [expected_event]

    assert access_grants.last_grant == (
        "to id-of-john-doe@ghga.de with some-other-iva-of-john for DS003"
        " from 2021-06-01 00:00:00+00:00 until 2021-12-31 23:59:00+00:00"
    )


async def test_set_status_to_allowed_without_iva():
    """Test setting the status of a request from pending to allowed without any IVA."""
    original_request = await dao.get_by_id("request-id-4")
    original_dict = original_request.model_dump()
    assert original_dict.pop("iva_id") is None
    assert original_dict.pop("status") == AccessRequestStatus.PENDING
    assert original_dict.pop("status_changed") is None
    assert original_dict.pop("changed_by") is None
    reset()

    with pytest.raises(
        repository.AccessRequestMissingIva, match="An IVA ID must be specified"
    ):
        await repository.update(
            "request-id-4",
            status=AccessRequestStatus.ALLOWED,
            auth_context=auth_context_steward,
        )


async def test_set_status_to_allowed_with_error_when_granting_access():
    """Test setting the status of a request when granting fails."""
    original_request = await dao.get_by_id("request-id-4")
    reset()
    access_grants.simulate_error = True

    with pytest.raises(
        repository.AccessRequestServerError,
        match="Could not register the download access grant",
    ):
        await repository.update(
            "request-id-4",
            iva_id="iva-id-1",
            status=AccessRequestStatus.ALLOWED,
            auth_context=auth_context_steward,
        )

    assert access_grants.last_grant == "to id-of-john-doe@ghga.de for DS007 failed"

    # make sure the status is not changed in this case, and no mails are sent out
    changed_request = dao.last_upsert
    assert changed_request is not None
    assert changed_request == original_request
    assert event_publisher.num_events == 0


async def test_set_status_to_allowed_when_it_is_already_allowed():
    """Test setting the status of a request to the same state."""
    request = await dao.get_by_id("request-id-1")
    assert request.status == AccessRequestStatus.ALLOWED

    reset()

    with pytest.raises(
        repository.AccessRequestError, match="Same status is already set"
    ):
        await repository.update(
            "request-id-1",
            iva_id="iva-id-1",
            status=AccessRequestStatus.ALLOWED,
            auth_context=auth_context_steward,
        )

    assert dao.last_upsert is None
    assert event_publisher.num_events == 0

    assert access_grants.last_grant == "nothing granted so far"


async def test_set_status_to_allowed_when_it_is_already_denied():
    """Test setting the status of a request to allowed that has already been denied."""
    request = await dao.get_by_id("request-id-3")
    assert request.status == AccessRequestStatus.DENIED

    reset()

    with pytest.raises(
        repository.AccessRequestError, match="Status cannot be reverted"
    ):
        await repository.update(
            "request-id-3",
            status=AccessRequestStatus.ALLOWED,
            auth_context=auth_context_steward,
        )

    assert access_grants.last_grant == "nothing granted so far"


async def test_set_status_of_non_existing_request():
    """Test setting the status of a request that does not exist."""
    reset()

    with pytest.raises(
        repository.AccessRequestNotFoundError, match="Access request not found"
    ):
        await repository.update(
            "request-non-existing-id",
            status=AccessRequestStatus.ALLOWED,
            auth_context=auth_context_steward,
        )

    assert dao.last_upsert is None
    assert event_publisher.num_events == 0
    assert access_grants.last_grant == "nothing granted so far"


async def test_set_status_when_not_a_data_steward():
    """Test setting the status of a request when not being a data steward."""
    reset()

    with pytest.raises(repository.AccessRequestError, match="Not authorized"):
        await repository.update(
            "request-id-4",
            status=AccessRequestStatus.ALLOWED,
            auth_context=auth_context_doe,
        )

    assert dao.last_upsert is None
    assert event_publisher.num_events == 0
    assert access_grants.last_grant == "nothing granted so far"
