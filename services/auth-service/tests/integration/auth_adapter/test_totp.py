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

"""Test the base TOTP functionality."""

from datetime import datetime
from random import randint
from typing import Optional
from urllib.parse import parse_qs, urlparse

import pyotp
from fastapi import status
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.utc_dates import now_as_utc
from pytest import mark

from auth_service.auth_adapter.core.session_store import SessionState
from auth_service.user_management.user_registry.models.dto import UserStatus

from ...fixtures.utils import (  # noqa: F401
    RE_USER_INFO_URL,
    USER_INFO,
    DummyUserDao,
    create_access_token,
    headers_for_session,
)
from .fixtures import (  # noqa: F401
    ClientWithSession,
    fixture_client,
    fixture_client_with_session,
    query_new_session,
)

pytestmark = mark.asyncio()


def get_valid_totp_code(
    secret: str, when: Optional[datetime] = None, offset: int = 0
) -> str:
    """Generate a valid TOTP code for the given secret."""
    if not when:
        when = datetime.utcnow()
    return pyotp.TOTP(secret).at(when, offset)


def get_invalid_totp_code(secret: str, when: Optional[datetime] = None) -> str:
    """Generate an invalid TOTP code for the given secret."""
    if not when:
        when = datetime.utcnow()
    # get the time codes for the tolerance interval
    # plus one more for possible timecode increment during the test
    valid_codes = {get_valid_totp_code(secret, when, offset) for offset in range(-1, 3)}
    for _ in range(10_000):
        code = f"{randint(0, 999_999):06d}"
        if code not in valid_codes:
            return code
    raise RuntimeError("Could not find an invalid TOTP code")


async def test_create_totp_token_without_session(client: AsyncTestClient):
    """Test that TOTP token creation without a session fails."""
    response = await client.post(
        "/totp-token", json={"user_id": "some-user-id", "force": False}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not logged in"}


async def test_create_totp_token_without_body(
    client_with_session: ClientWithSession,
):
    """Test that TOTP token creation without request body fails."""
    client, session = client_with_session[:2]
    response = await client.post(
        "/totp-token",
        headers=headers_for_session(session),
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_create_totp_token_with_unregistered_user(
    client_with_session: ClientWithSession,
):
    """Test that TOTP token creation with an unregistered user fails."""
    client, session = client_with_session[:2]
    response = await client.post(
        "/totp-token",
        json={"user_id": "unknown-user-id", "force": False},
        headers=headers_for_session(session),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not registered"}


async def test_create_totp_token_without_csrf_token(
    client_with_session: ClientWithSession,
):
    """Test that TOTP token creation without CSRF token fails."""
    client, session = client_with_session[:2]
    headers = headers_for_session(session)
    del headers["X-CSRF-Token"]
    response = await client.post(
        "/totp-token",
        json={"user_id": "john@ghga.de", "force": False},
        headers=headers,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid or missing CSRF token"}


async def test_create_totp_token_with_registered_user(
    client_with_session: ClientWithSession,
):
    """Test that TOTP token creation with a registered user is possible."""
    client, session = client_with_session[:2]
    response = await client.post(
        "/totp-token",
        json={"user_id": "john@ghga.de", "force": False},
        headers=headers_for_session(session),
    )
    assert response.status_code == status.HTTP_201_CREATED
    totp_response = response.json()
    assert isinstance(totp_response, dict)
    uri = totp_response.pop("uri")
    assert uri.startswith("otpauth://totp/GHGA:John%20Doe?secret=")
    assert uri.endswith("&issuer=GHGA")

    assert not totp_response

    session = await query_new_session(client, session)
    assert session.state is SessionState.NEW_TOTP_TOKEN


async def test_verify_totp_without_session(client: AsyncTestClient):
    """Test that TOTP verification without a session fails."""
    response = await client.post(
        "rpc/verify-totp", json={"user_id": "some-user-id", "totp": "123456"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not logged in"}


async def test_verify_totp_without_body(
    client_with_session: ClientWithSession,
):
    """Test that TOTP verification without request body fails."""
    client, session = client_with_session[:2]
    response = await client.post(
        "/rpc/verify-totp",
        headers=headers_for_session(session),
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_verify_totp_with_unregistered_user(
    client_with_session: ClientWithSession,
):
    """Test that TOTP token creation with an unregistered user fails."""
    client, session = client_with_session[:2]
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": "unknown-user-id", "totp": "123456"},
        headers=headers_for_session(session),
    )
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
        "/rpc/verify-totp",
        json={"user_id": "john@ghga.de", "totp": "123456"},
        headers=headers,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid or missing CSRF token"}


async def test_verify_totp(
    client_with_session: ClientWithSession,
):
    """Test verification of TOTP tokens."""
    client, session, _user_dao, user_token_dao = client_with_session
    headers = headers_for_session(session)
    user_id = "john@ghga.de"
    assert session.state is SessionState.REGISTERED
    # create a new TOTP token on the backend
    response = await client.post(
        "/totp-token", json={"user_id": user_id, "force": False}, headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    uri = response.json()["uri"]
    secret = parse_qs(urlparse(uri).query)["secret"][0]
    assert len(secret) == 32
    assert secret.isalnum()
    # make sure the backend state is now as expected
    session = await query_new_session(client, session)
    assert session.state is SessionState.NEW_TOTP_TOKEN
    # try to verify with invalid TOTP code
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": user_id, "totp": get_invalid_totp_code(secret)},
        headers=headers,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid TOTP code"}
    # verify with valid TOTP code
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": user_id, "totp": get_valid_totp_code(secret)},
        headers=headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text
    # make sure the backend state is now as expected
    session = await query_new_session(client, session)
    assert session.state is SessionState.AUTHENTICATED
    # check that the token has been moved to the database
    user_tokens = user_token_dao.user_tokens
    assert len(user_tokens) == 1
    user_token = user_tokens.get(user_id, None)
    assert user_token
    totp_token = user_token.totp_token
    assert len(totp_token.encrypted_secret) == 96
    assert totp_token.last_counter
    assert totp_token.counter_attempts == -1  # verified

    # decrease the TOTP counter so that we can re-login without waiting
    totp_token.last_counter -= 1

    # logout and re-login
    response = await client.post("/rpc/logout", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    session = await query_new_session(client)
    assert session.state is SessionState.HAS_TOTP_TOKEN
    headers = headers_for_session(session)
    # check that verification still works with rolled out token

    # again, first try to verify with invalid TOTP code
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": user_id, "totp": get_invalid_totp_code(secret)},
        headers=headers,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid TOTP code"}
    # then verify with valid TOTP code
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": user_id, "totp": get_valid_totp_code(secret)},
        headers=headers,
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
    client, session, _user_dao, user_token_dao = client_with_session
    headers = headers_for_session(session)
    user_id = "john@ghga.de"
    assert session.state is SessionState.REGISTERED
    # create a new TOTP token on the backend
    response = await client.post(
        "/totp-token", json={"user_id": user_id, "force": False}, headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    uri = response.json()["uri"]
    secret = parse_qs(urlparse(uri).query)["secret"][0]
    session = await query_new_session(client, session)
    assert session.state is SessionState.NEW_TOTP_TOKEN
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": user_id, "totp": get_valid_totp_code(secret)},
        headers=headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    # decrease the TOTP counter so that we can re-login without waiting
    totp_token = user_token_dao.user_tokens[user_id].totp_token
    totp_token.last_counter -= 1
    # make 6 attempts with invalid TOTP codes
    # (we might get 3 extra attempts due to time code increment during the test)
    for _ in range(6):
        response = await client.post(
            "/rpc/verify-totp",
            json={"user_id": user_id, "totp": get_invalid_totp_code(secret)},
            headers=headers,
        )
        assert response.json() == {"detail": "Invalid TOTP code"}
    # now the user should not be verified any more
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": user_id, "totp": get_valid_totp_code(secret)},
        headers=headers,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid TOTP code"}
    # reset the TOTP token to make sure it works again
    totp_token.counter_attempts = 0
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": user_id, "totp": get_valid_totp_code(secret)},
        headers=headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text


async def test_total_limit_totp(
    client_with_session: ClientWithSession,
):
    """Test that there is a total limit for code verification."""
    client, session, user_dao, user_token_dao = client_with_session
    headers = headers_for_session(session)

    user = user_dao.user
    assert user
    user_id = user.id
    assert user_id == "john@ghga.de"
    assert user.status is UserStatus.ACTIVE
    assert not user.status_change

    # Check that the user is authorized
    response = await client.post("/users", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert not response.text
    assert "Authorization" in response.headers

    assert session.state is SessionState.REGISTERED
    # create a new TOTP token on the backend
    response = await client.post(
        "/totp-token", json={"user_id": user_id, "force": False}, headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    uri = response.json()["uri"]
    secret = parse_qs(urlparse(uri).query)["secret"][0]
    session = await query_new_session(client, session)
    assert session.state is SessionState.NEW_TOTP_TOKEN
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": user_id, "totp": get_valid_totp_code(secret)},
        headers=headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    # decrease the TOTP counter so that we can re-login without waiting
    totp_token = user_token_dao.user_tokens[user_id].totp_token
    totp_token.last_counter -= 1

    # make 10 attempts with invalid TOTP codes
    for _ in range(10):
        response = await client.post(
            "/rpc/verify-totp",
            json={"user_id": user_id, "totp": get_invalid_totp_code(secret)},
            headers=headers,
        )
        assert response.json() == {"detail": "Invalid TOTP code"}
        totp_token.counter_attempts = 0  # suppress rate limiting

    # now the user should not be verified any more
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": user_id, "totp": get_valid_totp_code(secret)},
        headers=headers,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Too many failed attempts"}

    # check that the user account has been disabled
    user = user_dao.user
    assert user
    assert user.status is UserStatus.INACTIVE
    status_change = user.status_change
    assert status_change
    assert status_change.previous is UserStatus.ACTIVE
    assert status_change.by == user_id
    assert status_change.context == "Too many failed TOTP login attempts"
    assert status_change.change_date
    assert 0 <= (now_as_utc() - status_change.change_date).total_seconds() < 3

    # check that the user is not authorized any more
    response = await client.post("/users", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not logged in"}
    assert "Authorization" not in response.headers


async def test_recreate_existing_totp_token(
    client_with_session: ClientWithSession,
):
    """Test that TOTP tokens can be recreated."""
    client, session = client_with_session[:2]
    headers = headers_for_session(session)
    user_id = "john@ghga.de"
    assert session.state is SessionState.REGISTERED

    # create a new TOTP token on the backend
    response = await client.post(
        "/totp-token", json={"user_id": user_id, "force": False}, headers=headers
    )
    assert response.status_code == status.HTTP_201_CREATED
    uri = response.json()["uri"]
    secret = parse_qs(urlparse(uri).query)["secret"][0]
    session = await query_new_session(client, session)
    assert session.state is SessionState.NEW_TOTP_TOKEN
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": user_id, "totp": get_valid_totp_code(secret)},
        headers=headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # try to create a new TOTP token without force flag
    response = await client.post(
        "/totp-token",
        json={"user_id": "john@ghga.de", "force": False},
        headers=headers_for_session(session),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Cannot create TOTP token at this point"}

    # try to create a new TOTP token with force flag
    response = await client.post(
        "/totp-token",
        json={"user_id": "john@ghga.de", "force": True},
        headers=headers_for_session(session),
    )
    assert response.status_code == status.HTTP_201_CREATED
    uri = response.json()["uri"]
    new_secret = parse_qs(urlparse(uri).query)["secret"][0]
    assert session.state is SessionState.NEW_TOTP_TOKEN

    # cannot login with old secret any more
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": user_id, "totp": get_valid_totp_code(secret)},
        headers=headers,
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid TOTP code"}
    # but can login with new secret now
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": user_id, "totp": get_valid_totp_code(new_secret)},
        headers=headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
