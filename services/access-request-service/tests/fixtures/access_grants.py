# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""A mock of the internal download access API used by this service."""

from typing import Any
from uuid import UUID

import httpx2
from ghga_service_commons.api.mock_router import MockRouter
from pytest import fixture

__all__ = ["GRANT_ID", "AccessGrantsMock", "access_grants_mock_fixture"]

# The download access API is mounted under a configurable base URL,
# therefore the paths below are matched against the end of the request URLs only.
GRANT_PATH = "/users/{user_id}/ivas/{iva_id}/datasets/{dataset_id}"
GRANTS_PATH = r"/grants(\?.*)?"  # the query string is optional here
GRANT_ID_PATH = "/grants/{grant_id}"

# the ID of the access grant that is created by default
GRANT_ID = UUID("49be6738-f328-49e9-a7fb-3d266e1cabe9")


class AccessGrantsMock:
    """A mock of the internal download access API.

    All requests that are passed to the mocked API are recorded in `requests`,
    while the responses can be tailored to the individual test cases using the
    attributes that are documented below.
    """

    def __init__(self) -> None:
        """Create a mock of the download access API with default responses."""
        # the requests that have been passed to the mocked API
        self.requests: list[httpx2.Request] = []
        # the ID that is returned when an access grant is created
        self.grant_id: UUID = GRANT_ID
        # the payload that is returned when access grants are fetched
        self.grants: Any = []
        # status codes to be returned instead of the regular ones
        self.grant_access_status_code: int | None = None
        self.get_grants_status_code: int | None = None
        self.revoke_grant_status_code: int | None = None
        # an error to be raised instead of responding at all
        self.error: Exception | None = None

        router: MockRouter = MockRouter()
        router.post(GRANT_PATH)(self.grant_access)
        router.get(GRANTS_PATH)(self.get_grants)
        router.delete(GRANT_ID_PATH)(self.revoke_grant)
        self.router = router

    @property
    def last_request(self) -> httpx2.Request:
        """Get the last request that has been passed to the mocked API."""
        assert self.requests, "No request has been made to the download access API"
        return self.requests[-1]

    def as_transport(self) -> httpx2.MockTransport:
        """Get a transport that routes requests to this mock."""
        return self.router.as_transport()

    def _record(self, request: httpx2.Request) -> None:
        """Record the given request and raise the configured error, if any."""
        self.requests.append(request)
        if self.error is not None:
            raise self.error

    def grant_access(
        self, user_id: str, iva_id: str, dataset_id: str, request: httpx2.Request
    ) -> httpx2.Response:
        """Mock the creation of a download access grant."""
        self._record(request)
        if self.grant_access_status_code is not None:
            return httpx2.Response(self.grant_access_status_code)
        return httpx2.Response(201, json={"id": str(self.grant_id)})

    def get_grants(self, request: httpx2.Request) -> httpx2.Response:
        """Mock fetching the list of download access grants."""
        self._record(request)
        if self.get_grants_status_code is not None:
            return httpx2.Response(self.get_grants_status_code)
        return httpx2.Response(200, json=self.grants)

    def revoke_grant(self, grant_id: str, request: httpx2.Request) -> httpx2.Response:
        """Mock the revocation of a download access grant."""
        self._record(request)
        if self.revoke_grant_status_code is not None:
            return httpx2.Response(self.revoke_grant_status_code)
        return httpx2.Response(204)


@fixture(name="access_grants")
def access_grants_mock_fixture() -> AccessGrantsMock:
    """Get a mock of the internal download access API."""
    return AccessGrantsMock()
