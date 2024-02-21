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
    client, session = client_with_session
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
    client, session = client_with_session
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
    client, session = client_with_session
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
    """Test that TOTP token creation with an registered user is possible."""
    client, session = client_with_session
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


# TODO: add test for other states,
# but this needs the verification endpoint to be implemented
