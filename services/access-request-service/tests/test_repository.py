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

"""Test the access request repository"""

from collections.abc import AsyncIterator, Mapping
from datetime import timedelta
from operator import attrgetter
from typing import Any, NamedTuple, Optional

from ghga_service_commons.auth.ghga import AcademicTitle, AuthContext, UserStatus
from ghga_service_commons.utils.utc_dates import DateTimeUTC, now_as_utc
from pydantic import EmailStr
from pytest import mark, raises

from ars.core.models import (
    AccessRequest,
    AccessRequestCreationData,
    AccessRequestData,
    AccessRequestStatus,
)
from ars.core.repository import AccessRequestConfig, AccessRequestRepository
from ars.ports.outbound.access_grants import AccessGrantsPort
from ars.ports.outbound.dao import AccessRequestDaoPort, ResourceNotFoundError
from ars.ports.outbound.notification_emitter import NotificationEmitterPort

datetime_utc = DateTimeUTC.construct

ONE_HOUR = timedelta(seconds=60 * 60)
ONE_YEAR = timedelta(days=365)

IAT = now_as_utc()
EXP = IAT + ONE_HOUR

auth_context_doe = AuthContext(
    id="id-of-john-doe@ghga.de",
    name="John Doe",
    email=EmailStr("john@home.org"),
    title=AcademicTitle.DR,
    ext_id=None,
    role=None,
    iat=IAT,
    exp=EXP,
    status=UserStatus.ACTIVE,
)


auth_context_steward = AuthContext(
    id="id-of-rod-steward@ghga.de",
    name="Rod Steward",
    email=EmailStr("steward@ghga.de"),
    title=None,
    ext_id=None,
    role="data_steward@ghga.de",
    iat=IAT,
    exp=EXP,
    status=UserStatus.ACTIVE,
)


config = AccessRequestConfig(
    access_upfront_max_days=365,
    access_grant_min_days=30,
    access_grant_max_days=2 * 365,
    data_steward_email=auth_context_steward.email,
)


ACCESS_REQUESTS = [
    AccessRequest(
        id="request-id-1",
        user_id="id-of-john-doe@ghga.de",
        dataset_id="some-dataset",
        email=EmailStr("me@john-doe.name"),
        request_text="Can I access some dataset?",
        access_starts=datetime_utc(2020, 1, 1, 0, 0),
        access_ends=datetime_utc(2020, 12, 31, 23, 59),
        full_user_name="Dr. John Doe",
        request_created=datetime_utc(2019, 12, 9, 12, 0),
        status=AccessRequestStatus.ALLOWED,
        status_changed=datetime_utc(2019, 12, 16, 12, 0),
        changed_by="id-of-rod-steward@ghga.de",
    ),
    AccessRequest(
        id="request-id-2",
        user_id="id-of-john-doe@ghga.de",
        dataset_id="another-dataset",
        email=EmailStr("me@john-doe.name"),
        request_text="Can I access another dataset?",
        access_starts=datetime_utc(2020, 1, 1, 0, 0),
        access_ends=datetime_utc(2020, 12, 31, 23, 59),
        full_user_name="Dr. John Doe",
        request_created=datetime_utc(2019, 12, 9, 12, 0),
        status=AccessRequestStatus.ALLOWED,
        status_changed=datetime_utc(2019, 12, 16, 12, 0),
        changed_by="id-of-rod-steward@ghga.de",
    ),
    AccessRequest(
        id="request-id-3",
        user_id="id-of-john-doe@ghga.de",
        dataset_id="yet-another-dataset",
        email=EmailStr("me@john-doe.name"),
        request_text="Can I access yet another dataset?",
        access_starts=datetime_utc(2020, 1, 1, 0, 0),
        access_ends=datetime_utc(2020, 12, 31, 23, 59),
        full_user_name="Dr. John Doe",
        request_created=datetime_utc(2019, 12, 9, 12, 0),
        status=AccessRequestStatus.DENIED,
        status_changed=datetime_utc(2019, 12, 16, 12, 0),
        changed_by="id-of-rod-steward@ghga.de",
    ),
    AccessRequest(
        id="request-id-4",
        user_id="id-of-john-doe@ghga.de",
        dataset_id="new-dataset",
        email=EmailStr("me@john-doe.name"),
        request_text="Can I access a new dataset?",
        access_starts=datetime_utc(2021, 1, 1, 0, 0),
        access_ends=datetime_utc(2021, 12, 31, 23, 59),
        full_user_name="Dr. John Doe",
        request_created=datetime_utc(2020, 12, 7, 12, 0),
        status=AccessRequestStatus.PENDING,
        status_changed=None,
        changed_by=None,
    ),
    AccessRequest(
        id="request-id-5",
        user_id="id-of-jane-roe@ghga.de",
        dataset_id="some-dataset",
        email=EmailStr("me@jane-roe.name"),
        request_text="Can I access the same dataset as Joe?",
        access_starts=datetime_utc(2020, 1, 1, 0, 0),
        access_ends=datetime_utc(2020, 12, 31, 23, 59),
        full_user_name="Dr. Jane Roe",
        request_created=datetime_utc(2019, 12, 9, 12, 0),
        status=AccessRequestStatus.ALLOWED,
        status_changed=datetime_utc(2019, 12, 16, 12, 0),
        changed_by="id-of-rod-steward@ghga.de",
    ),
]


class AccessRequestDaoDummy(AccessRequestDaoPort):  # pyright: ignore
    """Dummy AccessRequest DAO for testing."""

    last_upsert: Optional[AccessRequest]

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
        self.last_upsert = AccessRequest(**dto.dict(), id="newly-created-id")
        return self.last_upsert

    async def update(self, dto: AccessRequest) -> None:
        """Update an existing resource."""
        self.last_upsert = dto


class NotificationRecord(NamedTuple):
    """Class that records a sent notification while testing."""

    recipient: str
    subject: str
    text: str


class NotificationEmitterDummy(NotificationEmitterPort):
    """Dummy notification emitter for testing."""

    notifications: dict[str, NotificationRecord]

    def reset(self) -> None:
        """Reset the recorded notification."""
        self.notifications = {}

    @property
    def num_notifications(self):
        """Get total number of recorded notifications."""
        return len(self.notifications)

    def notification_for(self, email: str) -> NotificationRecord:
        """Get recorded notification to the given email."""
        return self.notifications[email]

    async def notify(
        self, *, email: EmailStr, full_name: str, subject: str, text: str
    ) -> None:
        """Send a notification."""
        if email in self.notifications:
            raise RuntimeError(f"A notification to {email} was already sent.")
        self.notifications[email] = NotificationRecord(full_name, subject, text)


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
        dataset_id: str,
        valid_from: DateTimeUTC,
        valid_until: DateTimeUTC,
    ) -> None:
        """Grant download access."""
        if self.simulate_error:
            self.last_grant = f"to {user_id} for {dataset_id} failed"
            raise self.AccessGrantsError
        self.last_grant = (
            f"to {user_id} for {dataset_id} from {valid_from} until {valid_until}"
        )


dao = AccessRequestDaoDummy()
notification_emitter = NotificationEmitterDummy()
access_grants = AccessGrantsDummy()


def reset():
    """Reset dummy adapters."""
    dao.reset()
    notification_emitter.reset()
    access_grants.reset()


repository = AccessRequestRepository(
    config=config,
    access_request_dao=dao,
    notification_emitter=notification_emitter,
    access_grants=access_grants,
)


@mark.asyncio
async def test_can_create_request():
    """Test that users can create an access request for themselves"""
    access_starts = now_as_utc()
    access_ends = access_starts + ONE_YEAR
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-doe@ghga.de",
        dataset_id="some-dataset",
        email=EmailStr("me@john-doe.name"),
        request_text="Can I access some dataset?",
        access_starts=access_starts,
        access_ends=access_ends,
    )
    reset()
    creation_date = now_as_utc()

    request = await repository.create(creation_data, auth_context=auth_context_doe)

    assert request.id == "newly-created-id"
    assert request.user_id == "id-of-john-doe@ghga.de"
    assert request.dataset_id == "some-dataset"
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

    assert notification_emitter.num_notifications == 2
    notification = notification_emitter.notification_for("steward@ghga.de")
    assert notification.recipient == "Data Steward"
    assert "access request has been created" in notification.subject
    assert (
        notification.text
        == "Dr. John Doe requested to download the dataset some-dataset.\n\n"
        + "The specified contact email address is: me@john-doe.name"
    )
    notification = notification_emitter.notification_for("me@john-doe.name")
    assert notification.recipient == "Dr. John Doe"
    assert "Your data download access request" in notification.subject
    assert (
        notification.text
        == "Your request to download the dataset some-dataset has been registered.\n\n"
        + "You should be contacted by one of our data stewards"
        + " in the next three workdays."
    )

    assert access_grants.last_grant == "nothing granted so far"


@mark.asyncio
async def test_cannot_create_request_for_somebody_else():
    """Test that users cannot create an access request for somebody else"""
    access_starts = now_as_utc()
    access_ends = access_starts + ONE_YEAR
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-foo@ghga.de",
        dataset_id="some-dataset",
        email=EmailStr("me@john-doe.name"),
        request_text="Can I access some dataset?",
        access_starts=access_starts,
        access_ends=access_ends,
    )
    with raises(repository.AccessRequestError, match="Not authorized"):
        await repository.create(creation_data, auth_context=auth_context_doe)


@mark.asyncio
async def test_silently_correct_request_that_is_too_early():
    """Test that requests that are too early are silently corrected"""
    creation_date = now_as_utc()
    access_starts = creation_date - 0.5 * ONE_YEAR
    access_ends = access_starts + 1.5 * ONE_YEAR
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-doe@ghga.de",
        dataset_id="some-dataset",
        email=EmailStr("me@john-doe.name"),
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

    assert notification_emitter.num_notifications == 2


@mark.asyncio
async def test_cannot_create_request_too_much_in_advance():
    """Test that users cannot create an access request too much in advance"""
    access_starts = now_as_utc() + 1.5 * ONE_YEAR
    access_ends = access_starts + ONE_YEAR
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-doe@ghga.de",
        dataset_id="some-dataset",
        email=EmailStr("me@john-doe.name"),
        request_text="Can I access some dataset?",
        access_starts=access_starts,
        access_ends=access_ends,
    )
    reset()

    with raises(
        repository.AccessRequestInvalidDuration, match="Access start date is invalid"
    ):
        await repository.create(creation_data, auth_context=auth_context_doe)

    assert dao.last_upsert is None
    assert notification_emitter.num_notifications == 0


@mark.asyncio
async def test_cannot_create_request_too_short():
    """Test that users cannot create an access request that is too short"""
    access_starts = now_as_utc()
    access_ends = access_starts + timedelta(days=29)
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-doe@ghga.de",
        dataset_id="some-dataset",
        email=EmailStr("me@john-doe.name"),
        request_text="Can I access some dataset?",
        access_starts=access_starts,
        access_ends=access_ends,
    )
    reset()

    with raises(
        repository.AccessRequestInvalidDuration, match="Access end date is invalid"
    ):
        await repository.create(creation_data, auth_context=auth_context_doe)

    assert dao.last_upsert is None
    assert notification_emitter.num_notifications == 0


@mark.asyncio
async def test_cannot_create_request_too_long():
    """Test that users cannot create an access request that is too long"""
    access_starts = now_as_utc()
    access_ends = access_starts + 2.5 * ONE_YEAR
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-doe@ghga.de",
        dataset_id="some-dataset",
        email=EmailStr("me@john-doe.name"),
        request_text="Can I access some dataset?",
        access_starts=access_starts,
        access_ends=access_ends,
    )
    reset()

    with raises(
        repository.AccessRequestInvalidDuration, match="Access end date is invalid"
    ):
        await repository.create(creation_data, auth_context=auth_context_doe)

    assert dao.last_upsert is None
    assert notification_emitter.num_notifications == 0


@mark.asyncio
async def test_can_get_all_requests_as_data_steward():
    """Test that a data steward can get all requests."""
    requests = await repository.get(auth_context=auth_context_steward)
    assert requests == sorted(
        ACCESS_REQUESTS, key=attrgetter("request_created"), reverse=True
    )


@mark.asyncio
async def test_can_get_all_own_requests_as_requester():
    """Test that requesters can get their own requests."""
    requests = await repository.get(auth_context=auth_context_doe)
    assert 0 < len(requests) < len(ACCESS_REQUESTS)
    assert requests == sorted(
        (
            request.copy(update={"changed_by": None})  # data steward is hidden
            for request in ACCESS_REQUESTS
            if request.full_user_name == "Dr. John Doe"
        ),
        key=attrgetter("request_created"),
        reverse=True,
    )


@mark.asyncio
async def test_users_cannot_get_requests_of_other_users():
    """Test that non data stewards cannot get requests of others."""
    with raises(repository.AccessRequestError, match="Not authorized"):
        await repository.get(
            auth_context=auth_context_doe, user_id="id-of-jane-roe@ghga.de"
        )


@mark.asyncio
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


@mark.asyncio
async def test_data_steward_can_get_requests_for_specific_dataset():
    """Test getting requests for a specific dataset."""
    requests = await repository.get(
        auth_context=auth_context_doe, dataset_id="another-dataset"
    )
    assert len(requests) == 1
    assert requests == [
        request.copy(update={"changed_by": None})  # data steward is hidden
        for request in ACCESS_REQUESTS
        if request.dataset_id == "another-dataset"
    ]


@mark.asyncio
async def test_data_steward_can_get_pending_requests():
    """Test getting only the pending requests."""
    requests = await repository.get(
        auth_context=auth_context_doe, status=AccessRequestStatus.PENDING
    )
    assert len(requests) == 1
    assert requests == [
        request
        for request in ACCESS_REQUESTS
        if request.status == AccessRequestStatus.PENDING
    ]


@mark.asyncio
async def test_filtering_using_multiple_criteria():
    """Test filtering using multiple criteria at the same time."""
    requests = await repository.get(
        auth_context=auth_context_steward,
        user_id="id-of-john-doe@ghga.de",
        dataset_id="some-dataset",
        status=AccessRequestStatus.ALLOWED,
    )
    assert len(requests) == 1
    assert requests == [
        request
        for request in ACCESS_REQUESTS
        if request.user_id == "id-of-john-doe@ghga.de"
        and request.dataset_id == "some-dataset"
        and request.status == AccessRequestStatus.ALLOWED
    ]


@mark.asyncio
async def test_set_status_to_allowed():
    """Test setting the status of a request from pending to allowed."""
    original_request = await dao.get_by_id("request-id-4")
    original_dict = original_request.dict()
    assert original_dict.pop("status") == AccessRequestStatus.PENDING
    assert original_dict.pop("status_changed") is None
    assert original_dict.pop("changed_by") is None
    reset()

    await repository.update(
        "request-id-4",
        status=AccessRequestStatus.ALLOWED,
        auth_context=auth_context_steward,
    )

    changed_request = dao.last_upsert
    assert changed_request is not None
    changed_dict = changed_request.dict()
    assert changed_dict.pop("status") == AccessRequestStatus.ALLOWED
    status_changed = changed_dict.pop("status_changed")
    assert status_changed is not None
    assert 0 <= (now_as_utc() - status_changed).seconds < 5
    assert changed_dict.pop("changed_by") == "id-of-rod-steward@ghga.de"
    assert changed_dict == original_dict

    assert notification_emitter.num_notifications == 2
    notification = notification_emitter.notification_for("steward@ghga.de")
    assert notification.recipient == "Data Steward"
    assert "download access has been allowed" in notification.subject
    assert (
        notification.text
        == "The request by Dr. John Doe to download the dataset\n"
        + "new-dataset has now been registered as allowed\n"
        + "and the access has been granted."
    )
    notification = notification_emitter.notification_for("me@john-doe.name")
    assert notification.recipient == "Dr. John Doe"
    assert "Your data download access request has been accepted" in notification.subject
    assert (
        notification.text
        == "We are glad to inform you that your request to download the dataset\n"
        + "new-dataset has been accepted.\n\n"
        + "You can now start download the dataset as explained in the GHGA Data Portal."
    )

    assert (
        access_grants.last_grant == "to id-of-john-doe@ghga.de for new-dataset"
        " from 2021-01-01 00:00:00+00:00 until 2021-12-31 23:59:00+00:00"
    )


@mark.asyncio
async def test_set_status_to_allowed_with_error_when_granting_access():
    """Test setting the status of a request when granting fails."""
    original_request = await dao.get_by_id("request-id-4")
    reset()
    access_grants.simulate_error = True

    with raises(
        repository.AccessRequestError,
        match="Could not register the download access grant",
    ):
        await repository.update(
            "request-id-4",
            status=AccessRequestStatus.ALLOWED,
            auth_context=auth_context_steward,
        )

    assert (
        access_grants.last_grant == "to id-of-john-doe@ghga.de for new-dataset failed"
    )

    # make sure the status is not changed in this case, and no mails are sent out
    changed_request = dao.last_upsert
    assert changed_request is not None
    assert changed_request == original_request
    assert notification_emitter.num_notifications == 0


@mark.asyncio
async def test_set_status_to_allowed_when_it_is_already_allowed():
    """Test setting the status of a request to the same state."""
    request = await dao.get_by_id("request-id-1")
    assert request.status == AccessRequestStatus.ALLOWED

    reset()

    with raises(repository.AccessRequestError, match="Same status is already set"):
        await repository.update(
            "request-id-1",
            status=AccessRequestStatus.ALLOWED,
            auth_context=auth_context_steward,
        )

    assert dao.last_upsert is None
    assert notification_emitter.num_notifications == 0

    assert access_grants.last_grant == "nothing granted so far"


@mark.asyncio
async def test_set_status_to_allowed_when_it_is_already_denied():
    """Test setting the status of a request to allowed that has already been denied."""
    request = await dao.get_by_id("request-id-3")
    assert request.status == AccessRequestStatus.DENIED

    reset()

    with raises(repository.AccessRequestError, match="Status cannot be reverted"):
        await repository.update(
            "request-id-3",
            status=AccessRequestStatus.ALLOWED,
            auth_context=auth_context_steward,
        )

    assert access_grants.last_grant == "nothing granted so far"


@mark.asyncio
async def test_set_status_of_non_existing_request():
    """Test setting the status of a request that does not exist."""
    reset()

    with raises(
        repository.AccessRequestNotFoundError, match="Access request not found"
    ):
        await repository.update(
            "request-non-existing-id",
            status=AccessRequestStatus.ALLOWED,
            auth_context=auth_context_steward,
        )

    assert dao.last_upsert is None
    assert notification_emitter.num_notifications == 0
    assert access_grants.last_grant == "nothing granted so far"


@mark.asyncio
async def test_set_status_when_not_a_data_steward():
    """Test setting the status of a request when not being a data steward."""
    reset()

    with raises(repository.AccessRequestError, match="Not authorized"):
        await repository.update(
            "request-id-4",
            status=AccessRequestStatus.ALLOWED,
            auth_context=auth_context_doe,
        )

    assert dao.last_upsert is None
    assert notification_emitter.num_notifications == 0
    assert access_grants.last_grant == "nothing granted so far"
