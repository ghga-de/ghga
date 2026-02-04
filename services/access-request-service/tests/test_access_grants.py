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

"""Test the access grant adapter."""

import json
from collections.abc import AsyncGenerator
from datetime import timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from hexkit.utils import now_utc_ms_prec
from pytest_asyncio import fixture as async_fixture
from pytest_httpx import HTTPXMock

from ars.adapters.outbound.http import AccessGrantsAdapter, AccessGrantsConfig
from ars.core.models import BaseAccessGrant

pytestmark = pytest.mark.asyncio(loop_scope="session")


DOWNLOAD_ACCESS_URL = "http://test-access:1234/download-access"

USER_ID = UUID("2db49f46-7c35-4883-be19-bed49528e95c")
IVA_ID = UUID("72859ba4-ed8c-47a4-8df4-02f74c53a819")
DATASET_ID = "DS001"
DATE_NOW = now_utc_ms_prec()
VALID_FROM = DATE_NOW - timedelta(days=7)
VALID_UNTIL = DATE_NOW + timedelta(days=30)

GRANT_ID = UUID("49be6738-f328-49e9-a7fb-3d266e1cabe9")
GRANT = BaseAccessGrant(
    id=GRANT_ID,
    user_id=USER_ID,
    iva_id=IVA_ID,
    dataset_id=DATASET_ID,
    created=DATE_NOW - timedelta(days=14),
    valid_from=VALID_FROM,
    valid_until=VALID_UNTIL,
    user_name="John Doe",
    user_email="doe@home.org",
)

GRANT_URL = f"{DOWNLOAD_ACCESS_URL}/users/{USER_ID}/ivas/{IVA_ID}/datasets/{DATASET_ID}"
GRANTS_URL = f"{DOWNLOAD_ACCESS_URL}/grants"


@async_fixture(name="grants_adapter", scope="session", loop_scope="session")
async def fixture_grants_adapter() -> AsyncGenerator[AccessGrantsAdapter]:
    """Get configured access grants test adapter."""
    config = AccessGrantsConfig(download_access_url=DOWNLOAD_ACCESS_URL)
    async with AccessGrantsAdapter.construct(config=config) as adapter:
        yield adapter


async def test_grant_download_access(
    grants_adapter: AccessGrantsAdapter, httpx_mock: HTTPXMock
):
    """Test granting download access"""
    grant_access = grants_adapter.grant_download_access
    httpx_mock.add_response(method="POST", url=GRANT_URL, status_code=204)

    await grant_access(
        user_id=USER_ID,
        iva_id=IVA_ID,
        dataset_id=DATASET_ID,
        valid_from=VALID_FROM,
        valid_until=VALID_UNTIL,
    )

    request = httpx_mock.get_request()
    assert request
    assert json.loads(request.content) == {
        "valid_from": VALID_FROM.isoformat().replace("+00:00", "Z"),
        "valid_until": VALID_UNTIL.isoformat().replace("+00:00", "Z"),
    }


async def test_grant_download_access_with_invalid_dates(
    grants_adapter: AccessGrantsAdapter,
):
    """Test granting download access for invalid dates"""
    grant_access = grants_adapter.grant_download_access

    with pytest.raises(
        grants_adapter.AccessGrantsInvalidPeriodError, match="Invalid validity period"
    ):
        await grant_access(
            user_id=USER_ID,
            iva_id=IVA_ID,
            dataset_id=DATASET_ID,
            valid_from=VALID_UNTIL,
            valid_until=VALID_FROM,
        )


async def test_grant_download_access_with_server_error(
    grants_adapter: AccessGrantsAdapter, httpx_mock: HTTPXMock
):
    """Test granting download access when there is a server error"""
    grant_access = grants_adapter.grant_download_access
    httpx_mock.add_response(method="POST", url=GRANT_URL, status_code=500)

    with pytest.raises(
        grants_adapter.AccessGrantsError,
        match="Unexpected response status code 500",
    ):
        await grant_access(
            user_id=USER_ID,
            iva_id=IVA_ID,
            dataset_id=DATASET_ID,
            valid_from=VALID_FROM,
            valid_until=VALID_UNTIL,
        )


async def test_grant_download_access_with_timeout(
    grants_adapter: AccessGrantsAdapter, httpx_mock: HTTPXMock
):
    """Test granting download access when there is a network timeout"""
    grant_access = grants_adapter.grant_download_access
    httpx_mock.add_exception(httpx.ReadTimeout("Simulated network problem"))

    with pytest.raises(
        grants_adapter.AccessGrantsError, match="Simulated network problem"
    ):
        await grant_access(
            user_id=USER_ID,
            iva_id=IVA_ID,
            dataset_id=DATASET_ID,
            valid_from=VALID_FROM,
            valid_until=VALID_UNTIL,
        )


@pytest.mark.parametrize("with_params", [False, True])
@pytest.mark.parametrize("returned_grants", [[], [GRANT], [GRANT] * 3])
async def test_get_access_grants(
    with_params: bool,
    returned_grants: list[BaseAccessGrant],
    grants_adapter: AccessGrantsAdapter,
    httpx_mock: HTTPXMock,
):
    """Test fetching download access grants"""
    get_grants = grants_adapter.get_download_access_grants

    url = GRANTS_URL
    if with_params:
        url += f"?user_id={USER_ID}&iva_id={IVA_ID}&dataset_id={DATASET_ID}&valid=true"

    text = ",".join(grant.model_dump_json() for grant in returned_grants)
    text = f"[{text}]"

    httpx_mock.add_response(method="GET", url=url, status_code=200, text=text)

    params = (
        {"user_id": USER_ID, "iva_id": IVA_ID, "dataset_id": DATASET_ID, "valid": True}
        if with_params
        else {}
    )
    grants = await get_grants(**params)  # type: ignore[arg-type]

    assert isinstance(grants, list)
    assert all(isinstance(grant, BaseAccessGrant) for grant in grants)
    assert len(grants) == len(returned_grants)
    assert grants == returned_grants


async def test_get_access_grants_with_data_error(
    grants_adapter: AccessGrantsAdapter,
    httpx_mock: HTTPXMock,
):
    """Test fetching download access grants with data errors"""
    get_grants = grants_adapter.get_download_access_grants

    # Simulate a server response with missing user name
    text = GRANT.model_dump_json(exclude={"user_name"})
    text = f"[{text}]"

    httpx_mock.add_response(
        method="GET",
        url=GRANTS_URL,
        status_code=200,
        text=text,
    )

    with pytest.raises(
        grants_adapter.AccessGrantsError,
        match=r"Invalid data in response: .*\nuser_name\n.* required",
    ):
        await get_grants()


async def test_get_access_grants_with_server_error(
    grants_adapter: AccessGrantsAdapter,
    httpx_mock: HTTPXMock,
):
    """Test fetching download access grants with server error"""
    get_grants = grants_adapter.get_download_access_grants
    httpx_mock.add_response(method="GET", url=GRANTS_URL, status_code=500)

    with pytest.raises(
        grants_adapter.AccessGrantsError,
        match="Unexpected response status code 500",
    ):
        await get_grants()


async def test_get_access_grants_with_timeout(
    grants_adapter: AccessGrantsAdapter,
    httpx_mock: HTTPXMock,
):
    """Test fetching download access grants when there is a network timeout"""
    get_grants = grants_adapter.get_download_access_grants
    httpx_mock.add_exception(httpx.ReadTimeout("Simulated network problem"))

    with pytest.raises(
        grants_adapter.AccessGrantsError, match="Simulated network problem"
    ):
        await get_grants()


async def test_revoke_existing_access_grants(
    grants_adapter: AccessGrantsAdapter,
    httpx_mock: HTTPXMock,
):
    """Test revoking an existing download access grant"""
    revoke_grant = grants_adapter.revoke_download_access_grant

    url = f"{GRANTS_URL}/{GRANT_ID}"
    httpx_mock.add_response(method="DELETE", url=url, status_code=204)

    await revoke_grant(GRANT_ID)

    # make sure the request was sent
    request = httpx_mock.get_request()
    assert request
    assert request.method == "DELETE"
    assert str(request.url) == url
    assert not request.content


async def test_revoke_non_existing_access_grants(
    grants_adapter: AccessGrantsAdapter,
    httpx_mock: HTTPXMock,
):
    """Test deleting a non-existing download access grant"""
    revoke_grant = grants_adapter.revoke_download_access_grant
    random_grant_id = uuid4()
    url = f"{GRANTS_URL}/{random_grant_id}"
    httpx_mock.add_response(method="DELETE", url=url, status_code=404)

    with pytest.raises(
        grants_adapter.AccessGrantNotFoundError,
        match=f"Grant with ID {random_grant_id} not found",
    ):
        await revoke_grant(random_grant_id)


async def test_revoke_access_grants_with_server_error(
    grants_adapter: AccessGrantsAdapter,
    httpx_mock: HTTPXMock,
):
    """Test deleting a download access grant when there is a server error"""
    revoke_grant = grants_adapter.revoke_download_access_grant

    url = f"{GRANTS_URL}/{GRANT_ID}"
    httpx_mock.add_response(method="DELETE", url=url, status_code=500)

    with pytest.raises(
        grants_adapter.AccessGrantsError,
        match="Unexpected response status code 500",
    ):
        await revoke_grant(GRANT_ID)


async def test_revoke_access_grants_with_timeout(
    grants_adapter: AccessGrantsAdapter,
    httpx_mock: HTTPXMock,
):
    """Test deleting a download access grants when there is a network timeout"""
    revoke_grant = grants_adapter.revoke_download_access_grant
    httpx_mock.add_exception(httpx.ReadTimeout("Simulated network problem"))

    with pytest.raises(
        grants_adapter.AccessGrantsError, match="Simulated network problem"
    ):
        await revoke_grant(GRANT_ID)
