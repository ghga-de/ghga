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

"""Test that the auth adapter checks sessions again against the user account."""

from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pyotp
import pytest
from fastapi import status
from httpx2 import Response

from auth_service.auth_adapter.core.session_store import Session, SessionState
from auth_service.auth_adapter.deps import SESSION_COOKIE, get_session_store
from auth_service.auth_adapter.rest.headers import get_bearer_token
from auth_service.claims_repository.deps import get_claim_dao
from auth_service.config import CONFIG
from auth_service.user_registry.models.ivas import IvaState
from auth_service.user_registry.models.users import UserStatus
from tests.fixtures.constants import DATA_STEWARD_IVA_ID

from ...fixtures.utils import get_claims_from_token, headers_for_session
from .fixtures import (
    AUTH_PATH,
    BareClient,
    ClientWithSession,
    fixture_bare_client,  # noqa: F401
    fixture_bare_client_with_session,  # noqa: F401
)

pytestmark = pytest.mark.asyncio()

API_PATH = "/api/some/path"
TOTP_TOKEN_PATH = AUTH_PATH + "/totp-token"
VERIFY_TOTP_PATH = AUTH_PATH + "/rpc/verify-totp"


async def authenticate(client: BareClient, session: Session) -> str:
    """Pass the second factor with a new TOTP token and return its secret."""
    headers = headers_for_session(session)
    response = await client.post(TOTP_TOKEN_PATH, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    secret = parse_qs(urlparse(response.json()["uri"]).query)["secret"][0]
    code = pyotp.TOTP(secret).now()
    headers["X-Authorization"] = f"Bearer TOTP:{code}"
    response = await client.post(VERIFY_TOTP_PATH, headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    return secret


async def let_check_become_due(client: BareClient, session: Session) -> None:
    """Move the last check of the session back by the check interval."""
    store = client.app.dependency_overrides[get_session_store]()
    stored_session = await store.get_session(session.session_id)
    assert stored_session
    assert stored_session.last_checked
    interval = timedelta(seconds=CONFIG.session_check_interval_seconds)
    stored_session.last_checked -= interval


def roles_from_response(response: Response) -> list[str]:
    """Get the roles from the internal token passed on by the auth adapter."""
    assert response.status_code == status.HTTP_200_OK
    internal_token = get_bearer_token(response.headers["Authorization"])
    assert internal_token
    return get_claims_from_token(internal_token)["roles"]


async def session_exists(client: BareClient, session: Session) -> bool:
    """Check whether the session still exists in the store."""
    store = client.app.dependency_overrides[get_session_store]()
    return bool(await store.get_session(session.session_id))


def assert_cookie_deleted(response: Response) -> None:
    """Assert that the response tells the client to delete the session cookie."""
    cookie = response.headers.get("Set-Cookie")
    assert cookie
    assert cookie.startswith(f'{SESSION_COOKIE}=""')
    assert "Max-Age=0" in cookie


async def test_no_check_within_interval(client_with_session: ClientWithSession):
    """Test that the user account is not read again within the check interval."""
    client, session, user_registry, _ = client_with_session
    await authenticate(client, session)
    headers = headers_for_session(session)

    user_registry.mock_user_dao.users.clear()  # would end the session if read

    response = await client.get(API_PATH, headers=headers)
    assert roles_from_response(response) == []
    assert await session_exists(client, session)


async def test_check_of_deleted_user(client_with_session: ClientWithSession):
    """Test that the session of a deleted user ends at the next check."""
    client, session, user_registry, _ = client_with_session
    await authenticate(client, session)
    headers = headers_for_session(session)

    user_registry.mock_user_dao.users.clear()
    await let_check_become_due(client, session)

    response = await client.get(API_PATH, headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "User account has been deleted"}
    assert "Authorization" not in response.headers
    assert_cookie_deleted(response)
    assert not await session_exists(client, session)


async def test_check_of_disabled_user(client_with_session: ClientWithSession):
    """Test that the session of a disabled user ends at the next check."""
    client, session, user_registry, _ = client_with_session
    await authenticate(client, session)
    headers = headers_for_session(session)

    user_dao = user_registry.mock_user_dao
    user_dao.users[-1] = user_dao.user.model_copy(
        update={"status": UserStatus.INACTIVE}
    )
    await let_check_become_due(client, session)

    response = await client.get(API_PATH, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "User account is disabled"}
    assert_cookie_deleted(response)
    assert not await session_exists(client, session)


async def test_check_of_changed_roles(client_with_session: ClientWithSession):
    """Test that a session gets roles granted after login at the next check."""
    client, session, user_registry, _ = client_with_session
    await authenticate(client, session)
    headers = headers_for_session(session)

    # make the user a data steward with a verified IVA
    claim_dao = client.app.dependency_overrides[get_claim_dao]()
    claim_dao.claims[0] = claim_dao.claims[0].model_copy(
        update={"user_id": user_registry.dummy_user.id}
    )
    user_registry.add_dummy_iva(id_=DATA_STEWARD_IVA_ID, state=IvaState.VERIFIED)

    response = await client.get(API_PATH, headers=headers)
    assert roles_from_response(response) == []

    await let_check_become_due(client, session)
    response = await client.get(API_PATH, headers=headers)
    assert roles_from_response(response) == ["data_steward"]

    # and loses the role again when the IVA is no longer verified
    user_registry.dummy_ivas[-1] = user_registry.dummy_ivas[-1].model_copy(
        update={"state": IvaState.UNVERIFIED}
    )
    await let_check_become_due(client, session)
    response = await client.get(API_PATH, headers=headers)
    assert roles_from_response(response) == []
    assert await session_exists(client, session)


async def test_check_of_replaced_totp_token(client_with_session: ClientWithSession):
    """Test that a session ends at the next check when its TOTP token is replaced."""
    client, session, _, user_token_dao = client_with_session
    await authenticate(client, session)
    headers = headers_for_session(session)

    user_id = session.user_id
    assert user_id
    user_token = await user_token_dao.get_by_id(user_id)
    user_token_dao.user_tokens[user_id] = user_token.model_copy(
        update={
            "totp_token": user_token.totp_token.model_copy(
                update={"encrypted_secret": "replaced"}
            )
        }
    )
    await let_check_become_due(client, session)

    response = await client.get(API_PATH, headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Session has ended"}
    assert_cookie_deleted(response)
    assert not await session_exists(client, session)


async def test_no_check_outside_api(client_with_session: ClientWithSession):
    """Test that requests outside the API do not check the session."""
    client, session, user_registry, _ = client_with_session
    await authenticate(client, session)
    headers = headers_for_session(session)

    user_registry.mock_user_dao.users.clear()
    await let_check_become_due(client, session)

    response = await client.get("/some/page", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert "Authorization" not in response.headers
    assert await session_exists(client, session)


async def test_check_before_second_factor(client_with_session: ClientWithSession):
    """Test that a session ends at the next check before the second factor."""
    client, session, user_registry, _ = client_with_session
    assert session.state is SessionState.REGISTERED
    headers = headers_for_session(session)

    user_registry.mock_user_dao.users.clear()
    await let_check_become_due(client, session)

    response = await client.get(API_PATH, headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "User account has been deleted"}
    assert not await session_exists(client, session)
