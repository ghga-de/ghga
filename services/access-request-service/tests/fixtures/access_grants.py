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

from ghga_service_commons.api.mock_api import ApiMock, endpoint, respond

__all__ = ["GRANT_ID", "AccessGrantsMock", "access_grants_mock_fixture"]

# the ID of the access grant that is created by default
GRANT_ID = UUID("49be6738-f328-49e9-a7fb-3d266e1cabe9")


class AccessGrantsMock(ApiMock):
    """A mock of the internal download access API.

    Each endpoint answers with the handler assigned to `on_grant_access`,
    `on_get_grants` or `on_revoke_grant`. Tests can swap those out with `respond(...)`,
    `fail_with(...)` or any other callable taking the request. All requests that are
    passed to the mocked API are recorded in `requests`.

    The download access API is mounted under a configurable base URL, and the tests
    using this mock do not all configure the same one, so the paths below are matched
    against the end of the request URLs only.
    """

    on_grant_access = endpoint(
        "POST",
        "/users/{user_id}/ivas/{iva_id}/datasets/{dataset_id}",
        respond(201, json={"id": str(GRANT_ID)}),
    )
    on_get_grants = endpoint("GET", "/grants", respond(200, json=[]))
    on_revoke_grant = endpoint("DELETE", "/grants/{grant_id}", respond(204))


@fixture(name="access_grants")
def access_grants_mock_fixture() -> AccessGrantsMock:
    """Get a mock of the internal download access API."""
    return AccessGrantsMock()
