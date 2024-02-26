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

"""Test handling TOTP in the auth adapter."""

from datetime import datetime
from random import randint
from typing import Optional
from urllib.parse import parse_qs, urlparse

import pyotp
from fastapi import status
from ghga_service_commons.api.testing import AsyncTestClient
from pytest import mark

from auth_service.auth_adapter.core.session_store import SessionState

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
    codes: set[str] = set()
    # get the time codes for the tolerance interval
    # plus one more for possible timecode increment during the test
    for offset in range(-1, 3):
        codes.add(get_valid_totp_code(secret, when, offset))
    for _ in range(10_000):
        code = f"{randint(0, 999_999):06d}"
        if code not in codes:
            return code
    raise RuntimeError("Could not find an invalid TOTP code")


@mark.asyncio
async def test_create_totp_token_without_session(client: AsyncTestClient):
    """Test that TOTP token creation without a session fails."""
    response = await client.post(
        "/totp-token", json={"user_id": "some-user-id", "force": False}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not logged in"}


@mark.asyncio
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


@mark.asyncio
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


@mark.asyncio
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


@mark.asyncio
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


@mark.asyncio
async def test_verify_totp_without_session(client: AsyncTestClient):
    """Test that TOTP verification without a session fails."""
    response = await client.post(
        "rpc/verify-totp", json={"user_id": "some-user-id", "totp": "123456"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not logged in"}


@mark.asyncio
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


@mark.asyncio
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


@mark.asyncio
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


@mark.asyncio
async def test_verify_totp(
    client_with_session: ClientWithSession,
):
    """Test verification of TOTP tokens."""
    client, session, user_token_dao = client_with_session
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
    assert totp_token.counter
    assert totp_token.attempts == -1  # verified

    # decrease the TOTP counter so that we can re-login without waiting
    totp_token.counter -= 1

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


@mark.asyncio
async def test_brute_force_totp(
    client_with_session: ClientWithSession,
):
    """Test that a bruce force attack fails."""
    client, session, user_token_dao = client_with_session
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
    totp_token.counter -= 1
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
    totp_token.attempts = 0
    response = await client.post(
        "/rpc/verify-totp",
        json={"user_id": user_id, "totp": get_valid_totp_code(secret)},
        headers=headers,
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not response.text


@mark.asyncio
async def test_recreate_existing_totp_token(
    client_with_session: ClientWithSession,
):
    """Test that TOTP tokens can be recreated."""
    client, session, user_token_dao = client_with_session
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
