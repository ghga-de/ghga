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

"""Test the base TOTP functionality."""

import logging
from datetime import datetime
from random import randint
from urllib.parse import parse_qs, urlparse

import pyotp
import pytest
from fastapi import status

from auth_service.auth_adapter.core.session_store import Session, SessionState
from auth_service.auth_adapter.deps import get_session_store
from auth_service.auth_adapter.ports.session_store import SessionStorePort
from auth_service.auth_adapter.rest.headers import get_bearer_token
from auth_service.claims_repository.deps import get_claim_dao
from auth_service.user_registry.models.ivas import IvaState
from auth_service.user_registry.models.users import UserStatus
from hexkit.utils import now_utc_ms_prec
from tests.fixtures.constants import DATA_STEWARD_IVA_ID, ID_OF_JOHN, SOME_USER_ID

from ...fixtures.utils import (
    USER_INFO,
    OidcProviderMock,
    get_claims_from_token,
    headers_for_session,
    mock_userinfo,
)
from .fixtures import (
    AUTH_PATH,
    BareClient,
    ClientWithSession,
    fixture_bare_client,  # noqa: F401
    fixture_bare_client_with_session,  # noqa: F401
    query_new_session,
    session_from_response,
)

pytestmark = pytest.mark.asyncio()


LOGOUT_PATH = AUTH_PATH + "/rpc/logout"
USERS_URL = AUTH_PATH + "/users"

TOTP_TOKEN_PATH = AUTH_PATH + "/totp-token"
VERIFY_TOTP_PATH = AUTH_PATH + "/rpc/verify-totp"


def get_valid_totp_code(
    secret: str, when: datetime | None = None, offset: int = 0
) -> str:
    """Generate a valid TOTP code for the given secret."""
    if not when:
        when = now_utc_ms_prec()
    return pyotp.TOTP(secret).at(when, counter_offset=offset)


def get_invalid_totp_code(secret: str, when: datetime | None = None) -> str:
    """Generate an invalid TOTP code for the given secret."""
    if not when:
        when = now_utc_ms_prec()
    # get the time codes for the tolerance interval
    # plus one more for possible timecode increment during the test
    valid_codes = {get_valid_totp_code(secret, when, offset) for offset in range(-1, 3)}
    for _ in range(10_000):
        code = f"{randint(0, 999_999):06d}"
        if code not in valid_codes:
            return code
    raise RuntimeError("Could not find an invalid TOTP code")


def with_totp_code(
    headers: dict[str, str], secret: str, valid: bool = True
) -> dict[str, str]:
    """Get headers for a valid or invalid TOTP code."""
    totp = get_valid_totp_code(secret) if valid else get_invalid_totp_code(secret)
    headers = headers.copy()
    headers["X-Authorization"] = f"Bearer TOTP:{totp}"
    return headers


async def remove_user_id_from_session(
    session: Session, session_store: SessionStorePort[Session]
):
    """Remove the user ID from the session in the backend."""
    assert session.user_id
    session_in_store = await session_store.get_session(session.session_id)
    assert session_in_store
    assert session_in_store.user_id == session.user_id
    session_in_store.user_id = None
    await session_store.save_session(session_in_store)


async def test_create_totp_token_with_invalid_force_flag(
    client_with_session: ClientWithSession,
):
    """Test that TOTP token creation with an invalid force flag fails."""
    client, session = client_with_session[:2]
    response = await client.post(
        TOTP_TOKEN_PATH + "?force=invalid", headers=headers_for_session(session)
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test_create_totp_token_without_user_id(
    client_with_session: ClientWithSession,
):
    """Test that TOTP token creation without a user ID fails."""
    client, session = client_with_session[:2]
    store = client.app.dependency_overrides[get_session_store]()
    await remove_user_id_from_session(session, store)
    response = await client.post(TOTP_TOKEN_PATH, headers=headers_for_session(session))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not registered"}


async def test_create_totp_token_without_csrf_token(
    client_with_session: ClientWithSession,
):
    """Test that TOTP token creation without CSRF token fails."""
    client, session = client_with_session[:2]
    headers = headers_for_session(session)
    del headers["X-CSRF-Token"]
    response = await client.post(TOTP_TOKEN_PATH, headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid or missing CSRF token"}


async def test_create_totp_token_with_registered_user(
    client_with_session: ClientWithSession,
):
    """Test that TOTP token creation with a registered user is possible."""
    client, session = client_with_session[:2]
    response = await client.post(TOTP_TOKEN_PATH, headers=headers_for_session(session))
    assert response.status_code == status.HTTP_201_CREATED
    totp_response = response.json()
    assert isinstance(totp_response, dict)
    uri = totp_response.pop("uri")
    assert uri.startswith("otpauth://totp/GHGA:John%20Doe?secret=")
    assert uri.endswith("&issuer=GHGA")

    assert not totp_response

    session = await query_new_session(client, session)
    assert session.state is SessionState.NEW_TOTP_TOKEN


async def test_verify_totp_without_session(bare_client: BareClient):
    """Test that TOTP verification without a session fails."""
    response = await bare_client.post(
        VERIFY_TOTP_PATH,
        json={"user_id": str(SOME_USER_ID), "totp": "123456"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not logged in"}


async def test_verify_totp_without_x_authorization_header(
    client_with_session: ClientWithSession,
):
    """Test that TOTP verification without X-Authorization header fails."""
    client, session = client_with_session[:2]
    response = await client.post(
        VERIFY_TOTP_PATH,
        headers=headers_for_session(session),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "No TOTP code provided"}


async def test_verify_totp_without_user_id(
    client_with_session: ClientWithSession,
):
    """Test that TOTP token creation without a user ID fails."""
    client, session = client_with_session[:2]
    store = client.app.dependency_overrides[get_session_store]()
    await remove_user_id_from_session(session, store)
    headers = headers_for_session(session).copy()
    headers["X-Authorization"] = "Bearer TOTP:123456"
    response = await client.post(VERIFY_TOTP_PATH, headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not registered"}


async def test_verify_totp_without_csrf_token(
    client_with_session: ClientWithSession,
):
    """Test that TOTP token creation without CSRF token fails."""
    client, session = client_with_session[:2]
    headers = headers_for_session(session)
    del headers["X-CSRF-Token"]
    response = await client.post(
        VERIFY_TOTP_PATH,
        json={"user_id": str(ID_OF_JOHN), "totp": "123456"},
        headers=headers,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid or missing CSRF token"}


async def test_verify_totp(
    client_with_session: ClientWithSession, oidc_provider: OidcProviderMock
):
    """Test verification of TOTP tokens."""
    client, session, user_registry, user_token_dao = client_with_session
    headers = headers_for_session(session)
    assert session.state is SessionState.REGISTERED
    # create a new TOTP token on the backend
    response = await client.post(TOTP_TOKEN_PATH, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    uri = response.json()["uri"]
    secret = parse_qs(urlparse(uri).query)["secret"][0]
    assert len(secret) == 32
    assert secret.isalnum()
    # make sure the backend state is now as expected
    session = await query_new_session(client, session)
    assert session.state is SessionState.NEW_TOTP_TOKEN
    # add a verified TOTP token to the user
    user_registry.add_dummy_iva(state=IvaState.VERIFIED)

    # try to verify with invalid TOTP code
    response = await client.post(
        VERIFY_TOTP_PATH,
        headers=with_totp_code(headers, secret, valid=False),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid TOTP code"}
    # check that the state of the IVA has not been reset
    assert user_registry.dummy_ivas[0].state is IvaState.VERIFIED
    # verify with valid TOTP code
    response = await client.post(
        VERIFY_TOTP_PATH,
        headers=with_totp_code(headers, secret),
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text
    # make sure the backend state is now as expected
    session = await query_new_session(client, session)
    assert session.state is SessionState.AUTHENTICATED
    # check that the token has been moved to the database
    user_tokens = user_token_dao.user_tokens
    assert len(user_tokens) == 1
    user_token = user_tokens.get(ID_OF_JOHN, None)
    assert user_token
    totp_token = user_token.totp_token
    assert len(totp_token.encrypted_secret) == 96
    assert totp_token.last_counter
    assert totp_token.counter_attempts == -1  # verified
    # check that the state of the IVA has been reset
    assert user_registry.dummy_ivas[0].state is IvaState.UNVERIFIED

    # decrease the TOTP counter so that we can re-login without waiting
    totp_token.last_counter -= 1

    # logout and re-login
    response = await client.post(LOGOUT_PATH, headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    mock_userinfo(oidc_provider, USER_INFO)
    session = await query_new_session(client)
    assert session.state is SessionState.HAS_TOTP_TOKEN
    headers = headers_for_session(session)
    # check that verification still works with rolled out token

    # again, first try to verify with invalid TOTP code
    response = await client.post(
        VERIFY_TOTP_PATH,
        headers=with_totp_code(headers, secret, valid=False),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid TOTP code"}
    # then verify with valid TOTP code
    response = await client.post(
        VERIFY_TOTP_PATH,
        headers=with_totp_code(headers, secret),
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text
    # make sure the backend state is now as expected
    session = await query_new_session(client, session)
    assert session.state is SessionState.AUTHENTICATED


async def test_rate_limiting_totp(
    client_with_session: ClientWithSession,
):
    """Test that the rate limiting for code verification works."""
    client, session, _user_registry, user_token_dao = client_with_session
    headers = headers_for_session(session)
    assert session.state is SessionState.REGISTERED
    # create a new TOTP token on the backend
    response = await client.post(TOTP_TOKEN_PATH, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    uri = response.json()["uri"]
    secret = parse_qs(urlparse(uri).query)["secret"][0]
    session = await query_new_session(client, session)
    assert session.state is SessionState.NEW_TOTP_TOKEN
    response = await client.post(
        VERIFY_TOTP_PATH,
        headers=with_totp_code(headers, secret),
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    # decrease the TOTP counter so that we can re-login without waiting
    totp_token = user_token_dao.user_tokens[ID_OF_JOHN].totp_token
    totp_token.last_counter -= 1
    # make 6 attempts with invalid TOTP codes
    # (we might get 3 extra attempts due to time code increment during the test)
    for _ in range(6):
        response = await client.post(
            VERIFY_TOTP_PATH,
            headers=with_totp_code(headers, secret, valid=False),
        )
        assert response.json() == {"detail": "Invalid TOTP code"}
    # now the user should not be verified any more
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    response = await client.post(
        VERIFY_TOTP_PATH,
        headers=with_totp_code(headers, secret),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid TOTP code"}
    # reset the TOTP token to make sure it works again
    totp_token.counter_attempts = 0
    response = await client.post(
        VERIFY_TOTP_PATH,
        headers=with_totp_code(headers, secret),
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text


async def test_total_limit_totp(
    client_with_session: ClientWithSession, caplog: pytest.LogCaptureFixture
):
    """Test that there is a total limit for code verification."""
    client, session, user_registry, user_token_dao = client_with_session
    headers = headers_for_session(session)

    user = user_registry.dummy_user
    user_id = user.id
    assert user.status is UserStatus.ACTIVE
    assert not user.status_change

    # Check that the user is authorized
    response = await client.post(USERS_URL, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert not response.text
    assert "Authorization" in response.headers

    assert session.state is SessionState.REGISTERED
    # create a new TOTP token on the backend
    response = await client.post(TOTP_TOKEN_PATH, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    uri = response.json()["uri"]
    secret = parse_qs(urlparse(uri).query)["secret"][0]
    session = await query_new_session(client, session)
    assert session.state is SessionState.NEW_TOTP_TOKEN
    response = await client.post(
        VERIFY_TOTP_PATH,
        headers=with_totp_code(headers, secret),
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    # decrease the TOTP counter so that we can re-login without waiting
    totp_token = user_token_dao.user_tokens[ID_OF_JOHN].totp_token
    totp_token.last_counter -= 1

    # make 10 attempts with invalid TOTP codes
    for _ in range(10):
        response = await client.post(
            VERIFY_TOTP_PATH,
            headers=with_totp_code(headers, secret, valid=False),
        )
        assert response.json() == {"detail": "Invalid TOTP code"}
        totp_token.counter_attempts = 0  # suppress rate limiting
    assert totp_token.total_attempts == 10

    # now the user should not be verified any more
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    caplog.set_level(
        logging.WARNING, logger="auth_service.auth_adapter.core.verify_totp"
    )
    caplog.clear()
    response = await client.post(
        VERIFY_TOTP_PATH,
        headers=with_totp_code(headers, secret),
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "User account is disabled"}

    warning_messages = [rec.getMessage() for rec in caplog.records]
    assert len(warning_messages) == 1
    assert warning_messages[0] == (
        f"Too many failed TOTP login attempts for user {user.id} (John Doe)"
    )

    # check that the user account has been disabled
    user = user_registry.dummy_user
    assert user.status is UserStatus.INACTIVE
    status_change = user.status_change
    assert status_change
    assert status_change.previous is UserStatus.ACTIVE
    assert status_change.by == user_id
    assert status_change.context == "Too many failed TOTP login attempts"
    assert status_change.change_date
    assert 0 <= (now_utc_ms_prec() - status_change.change_date).total_seconds() < 3
    totp_token = user_token_dao.user_tokens[user_id].totp_token
    # check that the TOTP token has been reset
    assert totp_token.total_attempts == 0

    # check that the user is not authorized any more
    response = await client.post(USERS_URL, headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not logged in"}
    assert "Authorization" not in response.headers


async def test_recreate_existing_totp_token(
    client_with_session: ClientWithSession,
):
    """Test that TOTP tokens can be recreated."""
    client, session = client_with_session[:2]
    user_registry = client_with_session.user_registry
    assert not user_registry.published_events

    headers = headers_for_session(session)
    assert session.state is SessionState.REGISTERED

    # create a new TOTP token on the backend
    response = await client.post(TOTP_TOKEN_PATH, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    uri = response.json()["uri"]
    secret = parse_qs(urlparse(uri).query)["secret"][0]
    session = await query_new_session(client, session)
    assert session.state is SessionState.NEW_TOTP_TOKEN
    response = await client.post(
        VERIFY_TOTP_PATH,
        headers=with_totp_code(headers, secret),
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    session = await query_new_session(client, session)
    assert session.state is SessionState.AUTHENTICATED

    assert not user_registry.published_events

    # try to create a new TOTP token without force flag
    response = await client.post(TOTP_TOKEN_PATH, headers=headers_for_session(session))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Cannot create TOTP token at this point"}

    assert not user_registry.published_events

    # try to create a new TOTP token with force flag
    response = await client.post(
        TOTP_TOKEN_PATH + "?force=true", headers=headers_for_session(session)
    )
    assert response.status_code == status.HTTP_201_CREATED
    uri = response.json()["uri"]
    new_secret = parse_qs(urlparse(uri).query)["secret"][0]
    session = await query_new_session(client, session)
    assert session.state is SessionState.NEW_TOTP_TOKEN

    # should not notify because the token had not been stored yet
    assert not user_registry.published_events

    # cannot login with old secret any more
    response = await client.post(
        VERIFY_TOTP_PATH,
        headers=with_totp_code(headers, secret),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid TOTP code"}
    # but can login with new secret now
    response = await client.post(
        VERIFY_TOTP_PATH,
        headers=with_totp_code(headers, new_secret),
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    session = await query_new_session(client, session)
    assert session.state is SessionState.AUTHENTICATED

    # try to create a new TOTP token with force flag again
    response = await client.post(
        TOTP_TOKEN_PATH + "?force=true", headers=headers_for_session(session)
    )
    assert response.status_code == status.HTTP_201_CREATED
    uri = response.json()["uri"]
    changed_secret = parse_qs(urlparse(uri).query)["secret"][0]
    assert changed_secret != new_secret
    session = await query_new_session(client, session)
    assert session.state is SessionState.NEW_TOTP_TOKEN

    # should notify because the token was overwritten
    assert user_registry.published_events == [("2fa_recreation", ID_OF_JOHN)]


async def test_recreate_totp_token_for_disabled_user(
    client_with_session: ClientWithSession,
):
    """Test that a user disabled after login cannot replace the TOTP token."""
    client, session, user_registry, user_token_dao = client_with_session
    headers = headers_for_session(session)

    # set up a TOTP token while the account is still active
    response = await client.post(TOTP_TOKEN_PATH, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    secret = parse_qs(urlparse(response.json()["uri"]).query)["secret"][0]
    response = await client.post(
        VERIFY_TOTP_PATH, headers=with_totp_code(headers, secret)
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    user_dao = user_registry.mock_user_dao
    user_token = await user_token_dao.get_by_id(user_dao.user.id)

    # log in again, so that the session has passed the first factor only
    response = await client.post(LOGOUT_PATH, headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    client.cookies.clear()
    session = await query_new_session(client)
    assert session.state is SessionState.HAS_TOTP_TOKEN
    headers = headers_for_session(session)

    user_dao.users[-1] = user_dao.user.model_copy(
        update={"status": UserStatus.INACTIVE}
    )

    # the session may still ask for a new TOTP token
    response = await client.post(TOTP_TOKEN_PATH + "?force=true", headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    new_secret = parse_qs(urlparse(response.json()["uri"]).query)["secret"][0]

    # but a code for the new token is not accepted
    response = await client.post(
        VERIFY_TOTP_PATH, headers=with_totp_code(headers, new_secret)
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "User account is disabled"}

    # the stored token is kept and the session has ended
    assert await user_token_dao.get_by_id(user_dao.user.id) is user_token
    assert not user_registry.published_events
    response = await client.post(TOTP_TOKEN_PATH, headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not logged in"}


async def test_verify_totp_for_deleted_user(client_with_session: ClientWithSession):
    """Test that a user deleted after login cannot complete the second factor."""
    client, session, user_registry, user_token_dao = client_with_session
    headers = headers_for_session(session)

    response = await client.post(TOTP_TOKEN_PATH, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    secret = parse_qs(urlparse(response.json()["uri"]).query)["secret"][0]

    user_registry.mock_user_dao.users.clear()

    response = await client.post(
        VERIFY_TOTP_PATH, headers=with_totp_code(headers, secret)
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "User account has been deleted"}

    # no token is stored and the session has ended
    assert not user_token_dao.user_tokens
    assert not user_registry.published_events
    response = await client.post(TOTP_TOKEN_PATH, headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not logged in"}


async def test_recreate_totp_token_clears_roles_of_all_sessions(
    client_with_session: ClientWithSession,
):
    """Test that no session keeps its roles when the TOTP token is replaced.

    Replacing the token resets the verified IVAs that the roles depend on.
    This must also hold for a second session that logged in before the reset.
    """
    client, session, user_registry, user_token_dao = client_with_session
    headers = headers_for_session(session)

    # set up a TOTP token
    response = await client.post(TOTP_TOKEN_PATH, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    secret = parse_qs(urlparse(response.json()["uri"]).query)["secret"][0]
    response = await client.post(
        VERIFY_TOTP_PATH, headers=with_totp_code(headers, secret)
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    response = await client.post(LOGOUT_PATH, headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # make the user a data steward with a verified IVA
    user_id = user_registry.dummy_user.id
    claim_dao = client.app.dependency_overrides[get_claim_dao]()
    claim_dao.claims[0] = claim_dao.claims[0].model_copy(update={"user_id": user_id})
    user_registry.add_dummy_iva(id_=DATA_STEWARD_IVA_ID, state=IvaState.VERIFIED)

    # log in twice, so that both sessions have passed the first factor only
    sessions = []
    for _ in range(2):
        client.cookies.clear()
        session = await query_new_session(client)
        assert session.state is SessionState.HAS_TOTP_TOKEN
        assert session.roles == ["data_steward"]
        sessions.append(session)
    client.cookies.clear()
    headers_a, headers_b = map(headers_for_session, sessions)

    # replace the TOTP token in the first session
    response = await client.post(TOTP_TOKEN_PATH + "?force=true", headers=headers_a)
    assert response.status_code == status.HTTP_201_CREATED
    new_secret = parse_qs(urlparse(response.json()["uri"]).query)["secret"][0]
    response = await client.post(
        VERIFY_TOTP_PATH, headers=with_totp_code(headers_a, new_secret)
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # complete the second factor with the new token in the second session,
    # in the next time step, since replay protection blocks the current one
    user_token = await user_token_dao.get_by_id(user_id)
    user_token.totp_token.last_counter -= 1
    response = await client.post(
        VERIFY_TOTP_PATH, headers=with_totp_code(headers_b, new_secret)
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # the client learns the new roles from the verification response
    session_b = session_from_response(response, sessions[1].session_id)
    assert session_b.state is SessionState.AUTHENTICATED
    assert session_b.roles == []

    # neither session carries the role into the internal token
    for headers in headers_a, headers_b:
        response = await client.get("/api/some/path", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        internal_token = get_bearer_token(response.headers["Authorization"])
        assert internal_token
        assert get_claims_from_token(internal_token)["roles"] == []
