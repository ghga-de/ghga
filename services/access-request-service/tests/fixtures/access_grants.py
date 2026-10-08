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

from uuid import UUID

from pytest import fixture

from ghga_service_commons.http.mock_api import MockApi, ResponseHandler, respond

__all__ = [
    "DOWNLOAD_ACCESS_URL",
    "GRANT_ID",
    "AccessGrantsMock",
    "access_grants_mock_fixture",
]

# where the service under test finds the download access API
DOWNLOAD_ACCESS_URL = "http://access"

# the ID of the access grant that is created by default
GRANT_ID = UUID("49be6738-f328-49e9-a7fb-3d266e1cabe9")


class AccessGrantsMock(MockApi):
    """A mock of the internal download access API, answering with success by default."""

    def __init__(self, base_url: str = DOWNLOAD_ACCESS_URL) -> None:
        super().__init__(base_url)
        self.on_grant_access: ResponseHandler = respond(201, json={"id": str(GRANT_ID)})
        self.on_get_grants: ResponseHandler = respond(200, json=[])
        self.on_revoke_grant: ResponseHandler = respond(204)
        self.route(
            "POST",
            "/users/{user_id}/ivas/{iva_id}/datasets/{dataset_id}",
            "on_grant_access",
        )
        self.route("GET", "/grants", "on_get_grants")
        self.route("DELETE", "/grants/{grant_id}", "on_revoke_grant")


@fixture(name="access_grants")
def access_grants_mock_fixture() -> AccessGrantsMock:
    """Get a mock of the internal download access API."""
    return AccessGrantsMock()
