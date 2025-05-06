# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Module containing the main FastAPI router and API endpoints."""

import logging
from enum import Enum
from typing import Annotated

from fastapi import (
    FastAPI,
    Form,
    HTTPException,
    Request,
    Response,
    Security,
    status,
)
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ghga_service_commons.api import configure_app
from pydantic import AnyHttpUrl

from ..config import CONFIG
from ..core.http_utils import get_original_url
from ..core.models import LoginInfo, OidcConfiguration, TokenResponse, UserInfo
from ..core.oidc_provider import Jwks, OidcProvider

log = logging.getLogger(__name__)

app = FastAPI()
configure_app(app, config=CONFIG)

oidc_provider = OidcProvider(CONFIG)

tags: list[str | Enum] = ["TestOP"]


@app.get(
    "/health",
    summary="health",
    tags=tags,
    status_code=status.HTTP_200_OK,
)
async def health():
    """Used to test if this service is alive"""
    return {"status": "OK"}


@app.get(
    "/.well-known/openid-configuration",
    summary="Get the OpenID connect configuration",
    tags=tags,
    status_code=status.HTTP_200_OK,
)
async def get_openid_configuration(request: Request) -> OidcConfiguration:
    """The OpenID discovery endpoint."""
    original_url = get_original_url(request)
    # remove the current route to get the base URL
    base_url = original_url.removesuffix(".well-known/openid-configuration")
    # construct the other URLs from the base URL
    authorization_endpoint = AnyHttpUrl(base_url + "authorize")
    token_endpoint = AnyHttpUrl(base_url + "token")
    userinfo_endpoint = AnyHttpUrl(base_url + "userinfo")
    jwks_uri = AnyHttpUrl(base_url + "jwks")
    return OidcConfiguration(
        authorization_endpoint=authorization_endpoint,
        token_endpoint=token_endpoint,
        userinfo_endpoint=userinfo_endpoint,
        issuer=CONFIG.issuer,
        jwks_uri=jwks_uri,
    )


@app.get(
    "/jwks",
    summary="Get the JSON Web Key Set of the OP",
    tags=tags,
    status_code=status.HTTP_200_OK,
)
async def get_jwks() -> Jwks:
    """Get the JSON Web Key Set of the test OP."""
    return oidc_provider.jwks


@app.post(
    "/login",
    summary="Log in as a test user",
    tags=tags,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "model": str,
            "description": "Access token has been created.",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Validation error in submitted data."
        },
    },
)
async def login(login_info: LoginInfo) -> Response:
    """Endpoint for logging in to the OP as a test user."""
    log.debug("Logging in with info: %s", login_info)
    try:
        token = oidc_provider.login(login_info)
    except (TypeError, ValueError) as error:
        log.info("Invalid login info: %s", error)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        ) from error
    log.debug("Created login token: %s", token)
    return Response(
        content=token, media_type="application/jwt", status_code=status.HTTP_201_CREATED
    )


@app.get(
    "/authorize",
    summary="OIDC Authorization Endpoint",
    tags=tags,
    status_code=status.HTTP_302_FOUND,
    responses={
        status.HTTP_302_FOUND: {"description": "Redirected back to client."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Validation error in submitted data."
        },
    },
)
async def authorize(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
) -> RedirectResponse:
    """The authorization endpoint of the test OP.

    This authorizes the last logged in test user without checking credentials.
    """
    try:
        url = oidc_provider.authorize(
            response_type=response_type,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            state=state,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from error
    # Redirect back with code and state or error message
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@app.post(
    "/token",
    summary="OIDC Token Endpoint",
    tags=tags,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": TokenResponse,
            "description": "Access token has been granted.",
        },
        status.HTTP_400_BAD_REQUEST: {"description": "Error in submitted data."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Validation error in submitted data."
        },
    },
)
async def token(
    grant_type: str = Form(""),
    code: str = Form(""),
    redirect_uri: str = Form(""),
    client_id: str = Form(""),
) -> TokenResponse:
    """The token endpoint of the test OP."""
    try:
        return oidc_provider.token(
            grant_type=grant_type,
            code=code,
            redirect_uri=redirect_uri,
            client_id=client_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from error


@app.get(
    "/userinfo",
    summary="Get user information",
    tags=tags,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "model": UserInfo,
            "description": "User info has been fetched.",
        },
        status.HTTP_403_FORBIDDEN: {"description": "Not authorized to get user info."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Validation error in submitted data."
        },
    },
)
async def get_userinfo(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(HTTPBearer())],
) -> UserInfo:
    """The UserInfo endpoint of the test OP."""
    token = credentials.credentials
    log.debug("Getting user info for token: %s", token)
    try:
        return oidc_provider.user_info(token)
    except KeyError as error:
        log.info("User not found in cache.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
        ) from error
