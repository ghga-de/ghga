# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""FastAPI router and endpoints for authentication via ExtAuth protocol.

Note: If a path_prefix is used for the Emissary AuthService,
then this must be also specified in the config setting api_root_path.
"""

from typing import Annotated

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)
from ghga_service_commons.api import configure_app
from hexkit.protocols.dao import NoHitsFoundError, ResourceNotFoundError
from pydantic import SecretStr

from auth_service.config import CONFIG
from auth_service.user_management.claims_repository.core.utils import is_data_steward
from auth_service.user_management.claims_repository.deps import ClaimDao, get_claim_dao
from auth_service.user_management.user_registry.deps import (
    Depends,
    UserDao,
    UserRegistryPort,
    get_user_dao,
    get_user_registry,
)
from auth_service.user_management.user_registry.models.users import (
    User,
    UserStatus,
)

from .. import DESCRIPTION, TITLE, VERSION
from ..core.auth import (
    UserInfoError,
    get_user_info,
    internal_token_from_session,
)
from ..core.session_store import SessionState
from ..core.verify_totp import verify_totp
from ..deps import (
    SESSION_COOKIE,
    SessionDependency,
    SessionStoreDependency,
    TOTPHandlerDependency,
    UserTokenDao,
    get_user_token_dao,
)
from .basic import get_basic_auth_dependency
from .dto import TOTPTokenResponse
from .headers import get_bearer_token, pass_auth_response, session_to_header

app = FastAPI(title=TITLE, description=DESCRIPTION, version=VERSION)
configure_app(app, config=CONFIG)

basic_auth_dependency = get_basic_auth_dependency(app, CONFIG)
basic_auth_dependencies = [basic_auth_dependency] if basic_auth_dependency else None

# the auth adapter needs to handle all HTTP methods
READ_METHODS = ["GET", "HEAD", "OPTIONS"]
WRITE_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
ALL_METHODS = READ_METHODS + WRITE_METHODS

AUTH_PATH = CONFIG.api_ext_path.strip("/")
if AUTH_PATH:
    AUTH_PATH = "/" + AUTH_PATH


def add_allowed_route(route: str, write: bool = False):
    """Add a route that shall be passed through."""
    methods = WRITE_METHODS if write else READ_METHODS
    if route.endswith("/*"):
        route = route[:-1] + "{path:path}"
    elif "*" in route:
        route = route.replace("*", "{variable}")

    @app.api_route(route, methods=methods)
    async def allowed_route(
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> Response:
        """Unprotected route."""
        return pass_auth_response(request, authorization)


def add_allowed_routes():
    """Add all routes that shall be passed through."""
    for route in CONFIG.allow_read_paths:
        add_allowed_route(route, write=False)
    for route in CONFIG.allow_write_paths:
        add_allowed_route(route, write=True)


add_allowed_routes()


@app.post(
    AUTH_PATH + "/rpc/login",
    operation_id="login",
    tags=["users"],
    summary="Create or get user session",
    description="Endpoint used when a user wants to log in",
    dependencies=basic_auth_dependencies,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def login(  # noqa: C901, PLR0913
    session_store: SessionStoreDependency,
    session: SessionDependency,
    user_dao: Annotated[UserDao, Depends(get_user_dao)],
    token_dao: Annotated[UserTokenDao, Depends(get_user_token_dao)],
    claim_dao: Annotated[ClaimDao, Depends(get_claim_dao)],
    authorization: Annotated[str | None, Header()] = None,
    x_authorization: Annotated[str | None, Header()] = None,
) -> Response:
    """Create a new or get an existing user session.

    When creating a new user session based on an OIDC access token,
    first call the logout endpoint to remove an existing session cookie.
    """
    if session:
        session_created = False
    else:
        access_token = get_bearer_token(authorization, x_authorization)
        try:
            ext_id, user_name, user_email = get_user_info(access_token)
        except UserInfoError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(error)
            ) from error
        session = await session_store.create_session(
            ext_id=ext_id, user_name=user_name, user_email=user_email
        )
        session_created = True
    if session.user_id:
        try:
            user = await user_dao.get_by_id(session.user_id)
        except ResourceNotFoundError:
            user = None  # user has been deleted
    else:
        try:
            user = await user_dao.find_one(mapping={"ext_id": session.ext_id})
        except NoHitsFoundError:
            user = None  # user is not yet registered

    if user and user.status is not UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    async def _is_data_steward(user: User) -> bool:
        """Check whether the given user is a data steward."""
        return await is_data_steward(user.id, claim_dao=claim_dao)

    async def _has_totp_token(user: User) -> bool:
        """Check whether the given user has a TOTP token."""
        try:
            _ = await token_dao.get_by_id(user.id)
        except ResourceNotFoundError:
            return False
        return True

    await session_store.save_session(
        session,
        user=user,
        is_data_steward=_is_data_steward,
        has_totp_token=_has_totp_token,
    )

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.headers["X-Session"] = session_to_header(
        session, timeouts=session_store.timeouts
    )
    if session_created:
        response.set_cookie(
            key=SESSION_COOKIE,  # the name of the cookie
            value=session.session_id,
            secure=True,  # only send cookie over HTTPS
            httponly=True,  # don't allow JavaScript to access the cookie
            samesite="lax",  # allow browser to send cookies on top-level navigation
        )
    return response


@app.post(
    AUTH_PATH + "/rpc/logout",
    operation_id="logout",
    tags=["users"],
    summary="End user session",
    description="Endpoint used when a user wants to log out",
    dependencies=basic_auth_dependencies,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    session_store: SessionStoreDependency,
    session: SessionDependency,
) -> Response:
    """End the user session."""
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    if session:
        await session_store.delete_session(session.session_id)
        response.delete_cookie(
            key=SESSION_COOKIE,
            # must use the same params as in set_cookie
            secure=True,
            httponly=True,
            samesite="lax",
        )
    return response


@app.post(
    AUTH_PATH + "/users",
    operation_id="post_user",
    tags=["users"],
    summary="Register a user",
    description="Handle the endpoint to register a new user",
    dependencies=basic_auth_dependencies,
    status_code=status.HTTP_200_OK,
)
async def post_user(
    request: Request,
    session_store: SessionStoreDependency,
    session: SessionDependency,
) -> Response:
    """Register a user."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in"
        )
    await session_store.save_session(session)
    internal_token = internal_token_from_session(session)
    return pass_auth_response(request, f"Bearer {internal_token}")


@app.put(
    AUTH_PATH + "/users/{id}",
    operation_id="put_user",
    tags=["users"],
    summary="Update a user",
    description="Handle the endpoint to update an existing user",
    dependencies=basic_auth_dependencies,
    status_code=status.HTTP_200_OK,
)
async def put_user(
    id_: Annotated[
        str,
        Path(
            ...,
            alias="id",
            description="Internal ID",
        ),
    ],
    request: Request,
    session_store: SessionStoreDependency,
    session: SessionDependency,
) -> Response:
    """Update a user."""
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in"
        )
    if not session.user_id or id_ != session.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not registered"
        )
    await session_store.save_session(session)
    internal_token = internal_token_from_session(session)
    return pass_auth_response(request, f"Bearer {internal_token}")


@app.post(
    AUTH_PATH + "/totp-token",
    operation_id="create_new_totp_token",
    tags=["totp"],
    summary="Create a new TOTP token",
    description="Endpoint used to create or replace a TOTP token",
    dependencies=basic_auth_dependencies,
    status_code=status.HTTP_201_CREATED,
)
async def create_new_totp_token(
    session_store: SessionStoreDependency,
    session: SessionDependency,
    totp_handler: TOTPHandlerDependency,
    force: bool = Query(False, title="Overwrite existing token"),
) -> TOTPTokenResponse:
    """Create a new TOTP token or replace an existing one.

    Set "force" to true in order to allow overwriting an existing token.

    Note: Since this endpoint is used via the ExtAuth protocol,
    the request body cannot be used to pass parameters.
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in"
        )
    if not session.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not registered"
        )
    state = session.state
    if not (
        state in (SessionState.REGISTERED, SessionState.NEW_TOTP_TOKEN)
        or (
            state in (SessionState.HAS_TOTP_TOKEN, SessionState.AUTHENTICATED) and force
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cannot create TOTP token at this point",
        )
    session.totp_token = totp_handler.generate_token()
    session.state = SessionState.NEW_TOTP_TOKEN
    await session_store.save_session(session)
    uri = totp_handler.get_provisioning_uri(session.totp_token, name=session.user_name)
    return TOTPTokenResponse(uri=SecretStr(uri))


@app.post(
    AUTH_PATH + "/rpc/verify-totp",
    operation_id="verify_totp",
    tags=["totp"],
    summary="Verify a TOTP code",
    description="Endpoint used to verify a TOTP code",
    dependencies=basic_auth_dependencies,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def rpc_verify_totp(  # noqa: PLR0913
    session_store: SessionStoreDependency,
    session: SessionDependency,
    totp_handler: TOTPHandlerDependency,
    user_registry: Annotated[UserRegistryPort, Depends(get_user_registry)],
    token_dao: Annotated[UserTokenDao, Depends(get_user_token_dao)],
    x_authorization: Annotated[
        str | None, Header(title="the TOTP code to verify")
    ] = None,
) -> Response:
    """Verify a TOTP token.

    The TOTP code is expected to be passed like a bearer token
    in the "X-Authorization" header.

    Note: Since this endpoint is used via the ExtAuth protocol,
    the request body cannot be used to pass the TOTP code.
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in"
        )

    totp = get_bearer_token(x_authorization)
    if totp:
        totp = totp.removeprefix("TOTP:")
    if not totp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No TOTP code provided"
        )

    await verify_totp(
        totp,
        session_store=session_store,
        session=session,
        totp_handler=totp_handler,
        user_registry=user_registry,
        token_dao=token_dao,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.api_route(
    "/{path:path}",
    methods=ALL_METHODS,
    dependencies=basic_auth_dependencies,
    status_code=status.HTTP_200_OK,
)
async def ext_auth(
    request: Request,
    session_store: SessionStoreDependency,
    session: SessionDependency,
) -> Response:
    """Implements the ExtAuth protocol to authenticate users via the API gateway.

    If a user session exists and is two-factor-authenticated, then an internal
    authentication token will be added to the response.
    """
    if session:
        await session_store.save_session(session)
        if session.state is SessionState.AUTHENTICATED:
            internal_token = internal_token_from_session(session)
            return pass_auth_response(request, f"Bearer {internal_token}")
    return pass_auth_response(request)
