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
#

"""Dependencies and dependency dummies for the auth adapter used in view definitions.

The dummies are overridden by the actual dependencies when preparing the application.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from ghga_service_commons.api.di import DependencyDummy

from .core.session_store import Session
from .core.totp import TOTPToken
from .ports.dao import UserTokenDao
from .ports.session_store import SessionStorePort
from .ports.totp import TOTPHandlerPort

__all__ = [
    "SessionDependency",
    "SessionStoreDependency",
    "TOTPHandlerDependency",
    "UserTokenDaoDependency",
    "get_session_store",
    "get_totp_handler",
    "get_user_token_dao",
]

SESSION_COOKIE = "session"
CSRF_TOKEN_HEADER = "X-CSRF-Token"  # noqa: S105
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


get_session_store = DependencyDummy("session_store")
get_totp_handler = DependencyDummy("totp_handler")
get_user_token_dao = DependencyDummy("user_token_dao")


SessionStoreDependency = Annotated[
    SessionStorePort[Session], Depends(get_session_store)
]
TOTPHandlerDependency = Annotated[TOTPHandlerPort[TOTPToken], Depends(get_totp_handler)]
UserTokenDaoDependency = Annotated[UserTokenDao, Depends(get_user_token_dao)]


async def get_session(
    store: SessionStoreDependency,
    request: Request,
) -> Session | None:
    """Get the current session.

    Also checks the CSRF token if this is a write request.
    """
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return None
    session = await store.get_session(session_id)
    if not session:
        return None
    method = request.method
    if method in WRITE_METHODS:
        csrf_token = request.headers.get(CSRF_TOKEN_HEADER)
        if not csrf_token or csrf_token != session.csrf_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing CSRF token",
            )
    return session


SessionDependency = Annotated[Session | None, Depends(get_session)]
