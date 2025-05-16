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

"""Test the access request repository"""

from collections.abc import AsyncIterator, Mapping
from datetime import timedelta
from operator import attrgetter
from typing import Any

import pytest
from ghga_service_commons.auth.ghga import AcademicTitle, AuthContext
from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc, utc_datetime
from hexkit.custom_types import ID
from hexkit.protocols.dao import ResourceAlreadyExistsError

from ars.core.models import (
    AccessRequest,
    AccessRequestCreationData,
    AccessRequestPatchData,
    AccessRequestStatus,
    Dataset,
)
from ars.core.repository import AccessRequestConfig, AccessRequestRepository
from ars.ports.outbound.access_grants import AccessGrantsPort
from ars.ports.outbound.daos import (
    AccessRequestDaoPort,
    DatasetDaoPort,
    ResourceNotFoundError,
)

from .fixtures.datasets import DATASET

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
    roles=[],
    iat=IAT,
    exp=EXP,
)


auth_context_steward = AuthContext(
    id="id-of-rod-steward@ghga.de",
    name="Rod Steward",
    email="steward@ghga.de",
    title=None,
    roles=["data_steward@ghga.de"],
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
        dataset_title="Dataset1",
        dac_alias="Some DAC1",
        email="me@john-doe.name",
        request_text="Can I access some dataset?",
        access_starts=IAT + timedelta(days=30),
        access_ends=IAT + timedelta(days=180),
        full_user_name="Dr. John Doe",
        request_created=IAT,
        status=AccessRequestStatus.ALLOWED,
        status_changed=IAT + timedelta(days=1),
        changed_by="id-of-rod-steward@ghga.de",
    ),
    AccessRequest(
        id="request-id-2",
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS002",
        dataset_title="Dataset2",
        dac_alias="Some DAC2",
        email="me@john-doe.name",
        request_text="Can I access another dataset?",
        access_starts=IAT + timedelta(days=42),
        access_ends=IAT + timedelta(days=420),
        full_user_name="Dr. John Doe",
        request_created=IAT,
        status=AccessRequestStatus.ALLOWED,
        status_changed=IAT + timedelta(days=2),
        changed_by="id-of-rod-steward@ghga.de",
    ),
    AccessRequest(
        id="request-id-3",
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS003",
        dataset_title="Dataset3",
        dac_alias="Some DAC3",
        email="me@john-doe.name",
        request_text="Can I access yet another dataset?",
        access_starts=IAT + timedelta(days=1),
        access_ends=IAT + timedelta(days=90),
        full_user_name="Dr. John Doe",
        request_created=IAT,
        status=AccessRequestStatus.DENIED,
        status_changed=IAT + timedelta(days=3),
        changed_by="id-of-rod-steward@ghga.de",
    ),
    AccessRequest(
        id="request-id-4",
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS007",
        dataset_title="Dataset7",
        dac_alias="Some DAC7",
        email="me@john-doe.name",
        request_text="Can I access a new dataset?",
        access_starts=IAT + timedelta(days=50),
        access_ends=IAT + timedelta(days=500),
        full_user_name="Dr. John Doe",
        request_created=IAT,
        status=AccessRequestStatus.PENDING,
        status_changed=None,
        changed_by=None,
    ),
    AccessRequest(
        id="request-id-5",
        user_id="id-of-jane-roe@ghga.de",
        dataset_id="DS001",
        dataset_title="Dataset1",
        dac_alias="Some DAC",
        email="me@jane-roe.name",
        request_text="Can I access the same dataset as Joe?",
        access_starts=IAT + timedelta(days=5),
        access_ends=IAT + timedelta(days=200),
        full_user_name="Dr. Jane Roe",
        request_created=IAT,
        status=AccessRequestStatus.ALLOWED,
        status_changed=IAT + timedelta(days=4),
        changed_by="id-of-rod-steward@ghga.de",
    ),
    AccessRequest(
        id="request-id-6",
        user_id="id-of-john-doe@ghga.de",
        iva_id="iva-of-john",
        dataset_id="DS003",
        dataset_title="Dataset3",
        dac_alias="Some DAC3",
        email="me@john-doe.name",
        request_text="Can I access yet another dataset using this IVA?",
        access_starts=IAT + timedelta(days=5),
        access_ends=IAT + timedelta(days=250),
        full_user_name="Dr. John Doe",
        request_created=IAT,
        status=AccessRequestStatus.PENDING,
        status_changed=None,
        changed_by=None,
    ),
]


class AccessRequestDaoDummy(AccessRequestDaoPort):  # pyright: ignore
    """Dummy AccessRequest DAO for testing."""

    _requests: dict[ID, AccessRequest]

    def reset(self):
        """Reset the last recorded upsert."""
        self._requests = {request.id: request for request in ACCESS_REQUESTS}
        self.last_upsert = None

    def find_all(self, *, mapping: Mapping[str, Any]) -> AsyncIterator[AccessRequest]:
        """Find all records using a mapping."""

        async def async_iterator():
            for request in self._requests.values():
                if all(
                    value is None or value == getattr(request, key)
                    for key, value in mapping.items()
                ):
                    yield request

        return async_iterator()

    async def get_by_id(self, id_: ID) -> AccessRequest:
        """Get a resource by providing its ID."""
        try:
            return self._requests[id_]
        except KeyError as error:
            raise ResourceNotFoundError(id_=id_) from error

    async def insert(self, dto: AccessRequest) -> None:
        """Create a new record."""
        if dto.id in self._requests:
            raise ResourceAlreadyExistsError(id_=dto.id)
        self.last_upsert = self._requests[dto.id] = dto

    async def update(self, dto: AccessRequest) -> None:
        """Update an existing resource."""
        self.last_upsert = self._requests[dto.id] = dto


class DatasetDaoDummy(DatasetDaoPort):  # pyright: ignore
    """Dummy Dataset DAO for testing."""

    _datasets: dict[ID, Dataset]
    last_upsert: Dataset | None

    def reset(self):
        """Reset the last recorded upsert."""
        self._datasets = {}

    async def upsert(self, dto: Dataset) -> None:
        """Update the dataset if it already exists, create it otherwise."""
        self.last_upsert = self._datasets[dto.id] = dto

    async def get_by_id(self, id_: ID) -> Dataset:
        """Get a dataset by providing its ID.."""
        try:
            return self._datasets[id_]
        except KeyError as error:
            raise ResourceNotFoundError(id_=id_) from error

    async def delete(self, id_: ID) -> None:
        """Delete a dataset by providing its ID."""
        if id_ not in self._datasets:
            raise ResourceNotFoundError(id_=id_)
        del self._datasets[id_]


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


access_request_dao = AccessRequestDaoDummy()  # type: ignore
dataset_dao = DatasetDaoDummy()  # type: ignore
access_grants = AccessGrantsDummy()


@pytest.fixture(autouse=True)
def reset():
    """Reset dummy components before each test."""
    access_request_dao.reset()
    dataset_dao.reset()
    access_grants.reset()


repository = AccessRequestRepository(
    config=config,
    access_request_dao=access_request_dao,
    dataset_dao=dataset_dao,
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
    creation_date = now_as_utc()

    # Seed dataset so `repository.create` doesn't fail when it retrieves the dataset
    await repository.register_dataset(
        Dataset(
            id="DS001",
            title="A Great Dataset",
            description="This is a good dataset",
            dac_alias="Some DAC",
        )
    )
    request = await repository.create(creation_data, auth_context=auth_context_doe)

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

    assert access_request_dao.last_upsert == request
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

    # Seed dataset so `repository.create` doesn't fail when it retrieves the dataset
    await repository.register_dataset(
        Dataset(
            id="DS001",
            title="A Great Dataset",
            description="This is a good dataset",
            dac_alias="Some DAC",
        )
    )
    request = await repository.create(creation_data, auth_context=auth_context_doe)

    assert request.user_id == "id-of-john-doe@ghga.de"
    assert request.iva_id == "some-iva_id"
    assert request.dataset_id == "DS001"

    assert access_request_dao.last_upsert == request


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

    # Seed dataset so `repository.create` doesn't fail when it retrieves the dataset
    await repository.register_dataset(
        Dataset(
            id="DS001",
            title="A Great Dataset",
            description="This is a good dataset",
            dac_alias="Some DAC",
        )
    )
    request = await repository.create(creation_data, auth_context=auth_context_doe)

    assert 0 <= (request.request_created - creation_date).seconds < 5
    assert request.access_starts != creation_data.access_starts
    assert request.access_starts == request.request_created
    assert request.access_ends == creation_data.access_ends
    assert access_request_dao.last_upsert == request


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

    with pytest.raises(
        repository.AccessRequestInvalidDuration, match="Access start date is invalid"
    ):
        await repository.create(creation_data, auth_context=auth_context_doe)

    assert access_request_dao.last_upsert is None


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

    with pytest.raises(
        repository.AccessRequestInvalidDuration, match="Access end date is invalid"
    ):
        await repository.create(creation_data, auth_context=auth_context_doe)

    assert access_request_dao.last_upsert is None


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

    with pytest.raises(
        repository.AccessRequestInvalidDuration, match="Access end date is invalid"
    ):
        await repository.create(creation_data, auth_context=auth_context_doe)

    assert access_request_dao.last_upsert is None


async def test_cannot_create_request_nonexistent_dataset():
    """Make sure we get a DatasetNotFoundError when the requested dataset ID doesn't exist."""
    access_starts = now_as_utc()
    access_ends = access_starts + ONE_YEAR
    creation_data = AccessRequestCreationData(
        user_id="id-of-john-doe@ghga.de",
        dataset_id="DS404",
        email="me@john-doe.name",
        request_text="Can I access some dataset?",
        access_starts=access_starts,
        access_ends=access_ends,
    )

    with pytest.raises(repository.DatasetNotFoundError):
        _ = await repository.create(creation_data, auth_context=auth_context_doe)


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
    """Test updating the status of a request from pending to allowed."""
    original_request = await access_request_dao.get_by_id("request-id-4")
    original_dict = original_request.model_dump()
    assert original_dict.pop("iva_id") is None
    assert original_dict.pop("status") == AccessRequestStatus.PENDING
    assert original_dict.pop("status_changed") is None
    assert original_dict.pop("changed_by") is None

    await repository.update(
        "request-id-4",
        patch_data=AccessRequestPatchData(
            iva_id="some-iva", status=AccessRequestStatus.ALLOWED
        ),
        auth_context=auth_context_steward,
    )

    changed_request = access_request_dao.last_upsert
    assert changed_request is not None
    changed_dict = changed_request.model_dump()
    assert changed_dict.pop("status") == AccessRequestStatus.ALLOWED
    assert changed_dict.pop("iva_id") == "some-iva"
    status_changed = changed_dict.pop("status_changed")
    assert status_changed is not None
    assert 0 <= (now_as_utc() - status_changed).seconds < 5
    assert changed_dict.pop("changed_by") == "id-of-rod-steward@ghga.de"
    assert changed_dict == original_dict

    from_date = changed_dict["access_starts"]
    to_date = changed_dict["access_ends"]
    assert access_grants.last_grant == (
        "to id-of-john-doe@ghga.de with some-iva for DS007"
        f" from {from_date} until {to_date}"
    )


async def test_set_status_to_allowed_and_modify_duration():
    """Test allowing a request and modifying its duration at the same time."""
    original_request = await access_request_dao.get_by_id("request-id-4")
    original_dict = original_request.model_dump()
    assert original_dict.pop("iva_id") is None
    assert original_dict.pop("status") == AccessRequestStatus.PENDING
    assert original_dict.pop("status_changed") is None
    assert original_dict.pop("changed_by") is None
    assert original_dict.pop("access_starts") == IAT + timedelta(days=50)
    assert original_dict.pop("access_ends") == IAT + timedelta(days=500)

    await repository.update(
        "request-id-4",
        patch_data=AccessRequestPatchData(
            iva_id="some-iva",
            status=AccessRequestStatus.ALLOWED,
            access_starts=IAT + timedelta(days=60),
            access_ends=IAT + timedelta(days=360),
        ),
        auth_context=auth_context_steward,
    )

    changed_request = access_request_dao.last_upsert
    assert changed_request is not None
    changed_dict = changed_request.model_dump()
    assert changed_dict.pop("status") == AccessRequestStatus.ALLOWED
    assert changed_dict.pop("iva_id") == "some-iva"
    access_starts = changed_dict.pop("access_starts")
    assert access_starts == IAT + timedelta(days=60)
    access_ends = changed_dict.pop("access_ends")
    assert access_ends == IAT + timedelta(days=360)
    status_changed = changed_dict.pop("status_changed")
    assert status_changed is not None
    assert 0 <= (now_as_utc() - status_changed).seconds < 5
    assert changed_dict.pop("changed_by") == "id-of-rod-steward@ghga.de"
    assert changed_dict == original_dict

    assert access_grants.last_grant == (
        "to id-of-john-doe@ghga.de with some-iva for DS007"
        f" from {access_starts} until {access_ends}"
    )


async def test_set_status_to_allowed_reusing_iva():
    """Test setting the status of a request to allowed reusing the IVA."""
    original_request = await access_request_dao.get_by_id("request-id-6")
    original_dict = original_request.model_dump()
    assert original_dict["iva_id"] == "iva-of-john"
    assert original_dict.pop("status") == AccessRequestStatus.PENDING
    assert original_dict.pop("status_changed") is None
    assert original_dict.pop("changed_by") is None

    await repository.update(
        "request-id-6",
        patch_data=AccessRequestPatchData(status=AccessRequestStatus.ALLOWED),
        auth_context=auth_context_steward,
    )

    changed_request = access_request_dao.last_upsert
    assert changed_request is not None
    changed_dict = changed_request.model_dump()
    assert changed_dict.pop("status") == AccessRequestStatus.ALLOWED
    status_changed = changed_dict.pop("status_changed")
    assert status_changed is not None
    assert 0 <= (now_as_utc() - status_changed).seconds < 5
    assert changed_dict.pop("changed_by") == "id-of-rod-steward@ghga.de"
    assert changed_dict == original_dict

    from_date = changed_dict["access_starts"]
    to_date = changed_dict["access_ends"]
    assert access_grants.last_grant == (
        "to id-of-john-doe@ghga.de with iva-of-john for DS003"
        f" from {from_date} until {to_date}"
    )


async def test_set_status_to_allowed_overriding_iva():
    """Test setting the status of a request to allowed overriding the IVA."""
    original_request = await access_request_dao.get_by_id("request-id-6")
    original_dict = original_request.model_dump()
    assert original_dict.pop("iva_id") == "iva-of-john"
    assert original_dict.pop("status") == AccessRequestStatus.PENDING
    assert original_dict.pop("status_changed") is None
    assert original_dict.pop("changed_by") is None

    await repository.update(
        "request-id-6",
        patch_data=AccessRequestPatchData(
            iva_id="some-other-iva-of-john", status=AccessRequestStatus.ALLOWED
        ),
        auth_context=auth_context_steward,
    )

    changed_request = access_request_dao.last_upsert
    assert changed_request is not None
    changed_dict = changed_request.model_dump()
    assert changed_dict.pop("iva_id") == "some-other-iva-of-john"
    assert changed_dict.pop("status") == AccessRequestStatus.ALLOWED
    status_changed = changed_dict.pop("status_changed")
    assert status_changed is not None
    assert 0 <= (now_as_utc() - status_changed).seconds < 5
    assert changed_dict.pop("changed_by") == "id-of-rod-steward@ghga.de"
    assert changed_dict == original_dict

    from_date = changed_dict["access_starts"]
    to_date = changed_dict["access_ends"]
    assert access_grants.last_grant == (
        "to id-of-john-doe@ghga.de with some-other-iva-of-john for DS003"
        f" from {from_date} until {to_date}"
    )


async def test_set_status_to_allowed_without_iva():
    """Test setting the status of a request from pending to allowed without any IVA."""
    original_request = await access_request_dao.get_by_id("request-id-4")
    original_dict = original_request.model_dump()
    assert original_dict.pop("iva_id") is None
    assert original_dict.pop("status") == AccessRequestStatus.PENDING
    assert original_dict.pop("status_changed") is None
    assert original_dict.pop("changed_by") is None

    with pytest.raises(
        repository.AccessRequestMissingIva, match="An IVA ID must be specified"
    ):
        await repository.update(
            "request-id-4",
            patch_data=AccessRequestPatchData(status=AccessRequestStatus.ALLOWED),
            auth_context=auth_context_steward,
        )


async def test_set_status_to_allowed_with_error_when_granting_access():
    """Test setting the status of a request when granting fails."""
    original_request = await access_request_dao.get_by_id("request-id-4")
    access_grants.simulate_error = True

    with pytest.raises(
        repository.AccessRequestServerError,
        match="Could not register the download access grant",
    ):
        await repository.update(
            "request-id-4",
            patch_data=AccessRequestPatchData(
                iva_id="iva-id-1", status=AccessRequestStatus.ALLOWED
            ),
            auth_context=auth_context_steward,
        )

    assert access_grants.last_grant == "to id-of-john-doe@ghga.de for DS007 failed"

    # make sure the status is not changed in this case, and no mails are sent out
    changed_request = access_request_dao.last_upsert
    assert changed_request is not None
    assert changed_request == original_request


async def test_set_status_to_allowed_when_it_is_already_allowed():
    """Test setting the status of a request to the same state."""
    request = await access_request_dao.get_by_id("request-id-1")
    assert request.status == AccessRequestStatus.ALLOWED

    with pytest.raises(
        repository.AccessRequestError, match="Access request has already been processed"
    ):
        await repository.update(
            "request-id-1",
            patch_data=AccessRequestPatchData(
                iva_id="iva-id-1", status=AccessRequestStatus.ALLOWED
            ),
            auth_context=auth_context_steward,
        )

    assert access_request_dao.last_upsert is None

    assert access_grants.last_grant == "nothing granted so far"


async def test_set_status_to_allowed_when_it_is_already_denied():
    """Test setting the status of a request to allowed that has already been denied."""
    request = await access_request_dao.get_by_id("request-id-3")
    assert request.status == AccessRequestStatus.DENIED

    with pytest.raises(
        repository.AccessRequestError, match="Access request has already been processed"
    ):
        await repository.update(
            "request-id-3",
            patch_data=AccessRequestPatchData(status=AccessRequestStatus.ALLOWED),
            auth_context=auth_context_steward,
        )

    assert access_grants.last_grant == "nothing granted so far"


async def test_set_status_of_non_existing_request():
    """Test setting the status of a request that does not exist."""
    with pytest.raises(
        repository.AccessRequestNotFoundError, match="Access request not found"
    ):
        await repository.update(
            "request-non-existing-id",
            patch_data=AccessRequestPatchData(status=AccessRequestStatus.ALLOWED),
            auth_context=auth_context_steward,
        )

    assert access_request_dao.last_upsert is None
    assert access_grants.last_grant == "nothing granted so far"


async def test_set_status_when_not_a_data_steward():
    """Test setting the status of a request when not being a data steward."""
    with pytest.raises(repository.AccessRequestError, match="Not authorized"):
        await repository.update(
            "request-id-4",
            patch_data=AccessRequestPatchData(status=AccessRequestStatus.ALLOWED),
            auth_context=auth_context_doe,
        )

    assert access_request_dao.last_upsert is None
    assert access_grants.last_grant == "nothing granted so far"


async def test_set_access_date_when_request_is_already_allowed():
    """Test setting the access duration when request was already allowed."""
    request = await access_request_dao.get_by_id("request-id-1")
    assert request.status == AccessRequestStatus.ALLOWED

    with pytest.raises(
        repository.AccessRequestError,
        match="Access request has already been processed",
    ):
        await repository.update(
            "request-id-1",
            patch_data=AccessRequestPatchData(
                access_starts=IAT + timedelta(days=7),
                access_ends=IAT + timedelta(days=100),
            ),
            auth_context=auth_context_steward,
        )

    assert access_grants.last_grant == "nothing granted so far"


async def test_set_invalid_access_duration():
    """Test setting an invalid access duration."""
    request = await access_request_dao.get_by_id("request-id-4")
    assert request.status == AccessRequestStatus.PENDING

    with pytest.raises(
        repository.AccessRequestInvalidDuration,
        match="Access end date must be later than access start date",
    ):
        await repository.update(
            "request-id-4",
            patch_data=AccessRequestPatchData(
                access_starts=IAT + timedelta(days=30),
                access_ends=IAT + timedelta(days=29),
            ),
            auth_context=auth_context_steward,
        )

    assert access_grants.last_grant == "nothing granted so far"


async def test_set_invalid_access_start_date():
    """Test setting an invalid access start date."""
    request = await access_request_dao.get_by_id("request-id-4")
    assert request.status == AccessRequestStatus.PENDING

    with pytest.raises(
        repository.AccessRequestInvalidDuration,
        match="Access end date must be later than access start date",
    ):
        await repository.update(
            "request-id-4",
            patch_data=AccessRequestPatchData(
                access_starts=IAT + timedelta(days=500),
            ),
            auth_context=auth_context_steward,
        )

    assert access_grants.last_grant == "nothing granted so far"


async def test_set_invalid_access_end_date():
    """Test setting an invalid end date."""
    request = await access_request_dao.get_by_id("request-id-4")
    assert request.status == AccessRequestStatus.PENDING

    with pytest.raises(
        repository.AccessRequestInvalidDuration,
        match="Access end date must be later than access start date",
    ):
        await repository.update(
            "request-id-4",
            patch_data=AccessRequestPatchData(
                access_ends=utc_datetime(2020, 12, 31, 23, 59),
            ),
            auth_context=auth_context_steward,
        )

    assert access_grants.last_grant == "nothing granted so far"


async def test_set_past_access_start_date():
    """Test setting an invalid access start date."""
    request = await access_request_dao.get_by_id("request-id-4")
    assert request.status == AccessRequestStatus.PENDING

    now = now_as_utc()

    await repository.update(
        "request-id-4",
        patch_data=AccessRequestPatchData(
            access_starts=now - timedelta(days=30),
            access_ends=now + timedelta(days=180),
        ),
        auth_context=auth_context_steward,
    )

    request = await access_request_dao.get_by_id("request-id-4")
    assert request.status == AccessRequestStatus.PENDING
    assert now <= request.access_starts <= now + timedelta(seconds=5)
    assert request.access_ends == now + timedelta(days=180)

    assert access_grants.last_grant == "nothing granted so far"


async def test_extend_access_end_too_much():
    """Test setting an invalid access end date."""
    request = await access_request_dao.get_by_id("request-id-4")
    assert request.status == AccessRequestStatus.PENDING

    now = now_as_utc()

    with pytest.raises(
        repository.AccessRequestInvalidDuration,
        match="Access duration is too long",
    ):
        await repository.update(
            "request-id-4",
            patch_data=AccessRequestPatchData(
                access_starts=now + timedelta(days=30),
                access_ends=now + timedelta(days=9999),
            ),
            auth_context=auth_context_steward,
        )


async def test_set_ticket_id_and_notes():
    """Test setting the ticket ID and notes of a request."""
    request = await access_request_dao.get_by_id("request-id-4")
    assert request.status == AccessRequestStatus.PENDING

    # set ticket ID and internal note

    await repository.update(
        "request-id-4",
        patch_data=AccessRequestPatchData(
            ticket_id="ticket-id-4", internal_note="some internal note"
        ),
        auth_context=auth_context_steward,
    )

    changed_request = access_request_dao.last_upsert
    assert changed_request is not None
    changed_dict = changed_request.model_dump()
    assert changed_dict["ticket_id"] == "ticket-id-4"
    assert changed_dict["internal_note"] == "some internal note"
    assert changed_dict["note_to_requester"] is None

    # remove internal note and set note to requester

    await repository.update(
        "request-id-4",
        patch_data=AccessRequestPatchData(
            internal_note="", note_to_requester="some note to requester"
        ),
        auth_context=auth_context_steward,
    )

    changed_request = access_request_dao.last_upsert
    assert changed_request is not None
    changed_dict = changed_request.model_dump()
    assert changed_dict["ticket_id"] == "ticket-id-4"
    assert changed_dict["internal_note"] is None
    assert changed_dict["note_to_requester"] == "some note to requester"

    # status should not have changed

    assert changed_dict["status"] == AccessRequestStatus.PENDING.value


async def test_can_register_a_dataset():
    """Test that a dataset can be registered."""
    with pytest.raises(ResourceNotFoundError):
        await dataset_dao.get_by_id("some-dataset-id")
    await repository.register_dataset(DATASET)
    assert await dataset_dao.get_by_id("some-dataset-id") is DATASET


async def test_can_get_an_existing_dataset():
    """Test that an existing dataset can be fetched."""
    with pytest.raises(ResourceNotFoundError):
        await dataset_dao.get_by_id("some-dataset-id")
    await dataset_dao.upsert(DATASET)
    assert await repository.get_dataset("some-dataset-id") is DATASET


async def test_raises_error_when_getting_non_existing_dataset():
    """Test that getting a non-existing dataset raises an error."""
    with pytest.raises(repository.DatasetNotFoundError):
        await repository.get_dataset("some-dataset-id")
    await dataset_dao.upsert(DATASET)
    with pytest.raises(repository.DatasetNotFoundError):
        await repository.get_dataset("another-dataset-id")


async def test_can_update_dataset():
    """Test that an existing dataset can be updated."""
    original_dataset = DATASET.model_copy()
    await repository.register_dataset(original_dataset)
    dataset = await dataset_dao.get_by_id("some-dataset-id")
    assert dataset.title == "Some dataset"
    changed_dataset = original_dataset.model_copy(update={"title": "New title"})
    await repository.register_dataset(changed_dataset)
    dataset = await dataset_dao.get_by_id("some-dataset-id")
    assert dataset.title == "New title"


async def test_can_delete_an_existing_dataset():
    """Test that an existing dataset can be deleted."""
    await dataset_dao.upsert(DATASET)
    await repository.delete_dataset(dataset_id="some-dataset-id")
    with pytest.raises(ResourceNotFoundError):
        await dataset_dao.get_by_id("some-dataset-id")


async def test_raises_an_error_when_deleting_a_non_existing_dataset():
    """Test that deleting a non-existing dataset raises an error."""
    with pytest.raises(repository.DatasetNotFoundError):
        await repository.delete_dataset("some-dataset-id")


async def test_updates_pending_request_when_updating_its_dataset():
    """Test that updating a dataset updates pending access requests for it."""
    request = ACCESS_REQUESTS[3]
    assert request.status == AccessRequestStatus.PENDING
    assert request.status_changed is None

    dataset = DATASET.model_copy(update={"id": request.dataset_id})
    await dataset_dao.upsert(dataset)

    assert request.dataset_title != dataset.title
    assert request.dataset_description != dataset.description
    assert request.dac_alias != dataset.dac_alias

    await repository.register_dataset(dataset)

    request = await access_request_dao.get_by_id(request.id)
    assert request.dataset_title == dataset.title
    assert request.dataset_description == dataset.description
    assert request.dac_alias == dataset.dac_alias


@pytest.mark.parametrize(
    "status", [AccessRequestStatus.ALLOWED, AccessRequestStatus.DENIED]
)
async def test_does_not_alter_processed_request_when_updating_its_dataset(
    status: AccessRequestStatus,
):
    """Test that updating a dataset does not update processed access requests for it."""
    for request in ACCESS_REQUESTS:
        if request.status == status:
            break
    else:
        pytest.fail(f"No {status} access request found")
    status_changed = request.status_changed
    assert status_changed is not None

    dataset = DATASET.model_copy(update={"id": request.dataset_id})
    await dataset_dao.upsert(dataset)

    dataset_title = request.dataset_title
    assert dataset_title != dataset.title
    dataset_description = request.dataset_description
    assert dataset_description != dataset.description
    dac_alias = request.dac_alias
    assert dac_alias != dataset.dac_alias

    await repository.register_dataset(dataset)

    request = await access_request_dao.get_by_id(request.id)
    assert request.status == status
    assert request.status_changed == status_changed
    assert request.dataset_title == dataset_title
    assert request.dataset_description == dataset_description
    assert request.dac_alias == dac_alias


async def test_denies_pending_request_when_deleting_its_dataset():
    """Test that deleting a dataset denies pending access requests for it."""
    request = ACCESS_REQUESTS[3]
    assert request.status == AccessRequestStatus.PENDING
    assert request.status_changed is None

    dataset = DATASET.model_copy(update={"id": request.dataset_id})
    await dataset_dao.upsert(dataset)

    await repository.delete_dataset(dataset_id=dataset.id)
    request = await access_request_dao.get_by_id(request.id)
    assert request.status == AccessRequestStatus.DENIED
    assert request.status_changed is not None
    assert request.note_to_requester == "This dataset has been deleted"
    assert request.changed_by is None


@pytest.mark.parametrize(
    "status", [AccessRequestStatus.ALLOWED, AccessRequestStatus.DENIED]
)
async def test_keeps_processed_request_when_deleting_its_dataset(
    status: AccessRequestStatus,
):
    """Test that deleting a dataset does not change processed access requests for it."""
    for request in ACCESS_REQUESTS:
        if request.status == status:
            break
    else:
        pytest.fail(f"No {status} access request found")
    status_changed = request.status_changed
    assert status_changed is not None

    dataset = DATASET.model_copy(update={"id": request.dataset_id})
    await dataset_dao.upsert(dataset)
    await repository.delete_dataset(dataset_id=dataset.id)
    request = await access_request_dao.get_by_id(request.id)
    assert request.status == status
    assert request.status_changed == status_changed
