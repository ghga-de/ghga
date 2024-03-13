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

"""FastAPI dependencies for the auth adapter"""

from typing import Annotated, Optional

from fastapi import HTTPException, Request, status

from auth_service.deps import (
    Depends,
    MongoDbDaoFactory,
    get_config,
    get_mongodb_dao_factory,
)
from auth_service.user_management.user_registry.translators.dao import UserDaoConfig

from .adapters.memory_session_store import MemorySessionStore
from .core.session_store import Session, SessionConfig
from .core.totp import TOTPConfig, TOTPHandler, TOTPToken
from .ports.dao import UserTokenDao
from .ports.session_store import SessionStorePort
from .ports.totp import TOTPHandlerPort
from .translators.dao import UserTokenDaoFactory

__all__ = [
    "get_user_token_dao",
    "SessionStoreDependency",
    "SessionDependency",
]

SESSION_COOKIE = "session"
CSRF_TOKEN_HEADER = "X-CSRF-Token"  # noqa: S105
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

_session_store = None
_totp_handler = None


async def get_session_store(
    config: Annotated[SessionConfig, Depends(get_config)],
) -> SessionStorePort[Session]:
    """Get the session store."""
    global _session_store
    if not _session_store:
        _session_store = MemorySessionStore(config=config)
    return _session_store


async def get_session(
    store: Annotated[SessionStorePort[Session], Depends(get_session_store)],
    request: Request,
) -> Optional[Session]:
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


async def get_totp_handler(
    config: Annotated[TOTPConfig, Depends(get_config)],
) -> TOTPHandlerPort[TOTPToken]:
    """Get the TOTP handler."""
    global _totp_handler
    if not _totp_handler:
        _totp_handler = TOTPHandler(config=config)
    return _totp_handler


def get_user_token_dao_factory(
    config: UserDaoConfig = Depends(get_config),
    dao_factory: MongoDbDaoFactory = Depends(get_mongodb_dao_factory),
) -> UserTokenDaoFactory:
    """Get a user token DAO factory."""
    return UserTokenDaoFactory(config=config, dao_factory=dao_factory)


async def get_user_token_dao(
    dao_factory: UserTokenDaoFactory = Depends(get_user_token_dao_factory),
) -> UserTokenDao:
    """Get user token data access object."""
    return await dao_factory.get_user_token_dao()


SessionStoreDependency = Annotated[
    SessionStorePort[Session], Depends(get_session_store)
]

SessionDependency = Annotated[Optional[Session], Depends(get_session)]

TOTPHandlerDependency = Annotated[TOTPHandlerPort[TOTPToken], Depends(get_totp_handler)]
