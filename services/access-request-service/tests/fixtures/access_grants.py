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
#
"""A mock of the internal download access API used by this service."""

from typing import Any
from uuid import UUID

import httpx2
from pytest import fixture

from ghga_service_commons.api.mock_api import MockedApi, endpoint

__all__ = [
    "DOWNLOAD_ACCESS_URL",
    "GRANT_ID",
    "AccessGrantsMock",
    "access_grants_mock_fixture",
]

# where the download access API is served in the tests that do not say otherwise
DOWNLOAD_ACCESS_URL = "http://access"

# the ID of the access grant that is created by default
GRANT_ID = UUID("49be6738-f328-49e9-a7fb-3d266e1cabe9")


class AccessGrantsMock(MockedApi):
    """A mock of the internal download access API.

    All requests that are passed to the mocked API are recorded in `requests`,
    while the responses can be tailored to the individual test cases using the
    attributes that are documented below.
    """

    base_url = DOWNLOAD_ACCESS_URL

    def __init__(self, base_url: str = "") -> None:
        """Create a mock of the download access API with default responses."""
        super().__init__(base_url)
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

    def _fail_if_asked_to(self) -> None:
        """Raise the error the test configured, if it configured one."""
        if self.error is not None:
            raise self.error

    @endpoint("POST", "/users/{user_id}/ivas/{iva_id}/datasets/{dataset_id}")
    def on_grant_access(
        self, request: httpx2.Request, **path_variables: str
    ) -> httpx2.Response:
        """Mock the creation of a download access grant."""
        self._fail_if_asked_to()
        if self.grant_access_status_code is not None:
            return httpx2.Response(self.grant_access_status_code)
        return httpx2.Response(201, json={"id": str(self.grant_id)})

    @endpoint("GET", "/grants")
    def on_get_grants(self, request: httpx2.Request) -> httpx2.Response:
        """Mock fetching the list of download access grants."""
        self._fail_if_asked_to()
        if self.get_grants_status_code is not None:
            return httpx2.Response(self.get_grants_status_code)
        return httpx2.Response(200, json=self.grants)

    @endpoint("DELETE", "/grants/{grant_id}")
    def on_revoke_grant(
        self, request: httpx2.Request, **path_variables: str
    ) -> httpx2.Response:
        """Mock the revocation of a download access grant."""
        self._fail_if_asked_to()
        if self.revoke_grant_status_code is not None:
            return httpx2.Response(self.revoke_grant_status_code)
        return httpx2.Response(204)


@fixture(name="access_grants")
def access_grants_mock_fixture() -> AccessGrantsMock:
    """Get a mock of the internal download access API."""
    return AccessGrantsMock()
