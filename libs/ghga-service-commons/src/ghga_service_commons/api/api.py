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

"""Tools to setup and running FastAPI apps.

Contains functionality for initializing, configuring, and running
RESTful webapps with FastAPI.
"""
import asyncio
import logging
from collections.abc import Sequence
from functools import partial
from typing import Optional, Union

import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from hexkit.correlation import (
    InvalidCorrelationIdError,
    new_correlation_id,
    set_correlation_id,
    validate_correlation_id,
)
from pydantic import Field
from pydantic_settings import BaseSettings
from starlette.middleware.base import BaseHTTPMiddleware

from ghga_service_commons.httpyexpect.server.handlers.fastapi_ import (
    configure_exception_handler,
)

CORRELATION_ID_HEADER_NAME = "X-Correlation-ID"


log = logging.getLogger(__name__)


class ApiConfigBase(BaseSettings):
    """A base class with API-required config params.

    Inherit your config class from this class if you need
    to run an API backend.
    """

    host: str = Field("127.0.0.1", description="IP of the host.")
    port: int = Field(
        8080, description="Port to expose the server on the specified host"
    )
    auto_reload: bool = Field(
        False,
        description=(
            "A development feature."
            + " Set to `True` to automatically reload the server upon code changes"
        ),
    )
    workers: int = Field(1, description="Number of workers processes to run.")
    api_root_path: str = Field(
        "",
        description=(
            "Root path at which the API is reachable."
            + " This is relative to the specified host and port."
        ),
    )
    openapi_url: str = Field(
        "/openapi.json",
        description=(
            "Path to get the openapi specification in JSON format."
            + " This is relative to the specified host and port."
        ),
    )
    docs_url: str = Field(
        "/docs",
        description=(
            "Path to host the swagger documentation."
            + " This is relative to the specified host and port."
        ),
    )

    # Starlettes defaults will only be overwritten if a
    # non-None value is specified:
    cors_allowed_origins: Optional[Sequence[str]] = Field(
        None,
        examples=[["https://example.org", "https://www.example.org"]],
        description=(
            "A list of origins that should be permitted to make cross-origin requests."
            + " By default, cross-origin requests are not allowed."
            + " You can use ['*'] to allow any origin."
        ),
    )
    cors_allow_credentials: Optional[bool] = Field(
        None,
        examples=[["https://example.org", "https://www.example.org"]],
        description=(
            "Indicate that cookies should be supported for cross-origin requests."
            + " Defaults to False."
            + " Also, cors_allowed_origins cannot be set to ['*'] for credentials to be"
            + " allowed. The origins must be explicitly specified."
        ),
    )
    cors_allowed_methods: Optional[Sequence[str]] = Field(
        None,
        examples=[["*"]],
        description=(
            "A list of HTTP methods that should be allowed for cross-origin requests."
            + " Defaults to ['GET']. You can use ['*'] to allow all standard methods."
        ),
    )
    cors_allowed_headers: Optional[Sequence[str]] = Field(
        None,
        examples=[[]],
        description=(
            "A list of HTTP request headers that should be supported for cross-origin"
            + " requests. Defaults to []."
            + " You can use ['*'] to allow all headers."
            + " The Accept, Accept-Language, Content-Language and Content-Type headers"
            + " are always allowed for CORS requests."
        ),
    )
    generate_correlation_id: bool = Field(
        True,
        examples=[True, False],
        description=(
            "A flag, which, if False, will result in an error when inbound requests don't"
            + " possess a correlation ID. If True, requests without a correlation ID will"
            + " be assigned a newly generated ID in the correlation ID middleware function."
        ),
    )


def set_header_correlation_id(request: Request, correlation_id: str):
    """Set the correlation ID on the request header. Modifies the header in-place."""
    headers = request.headers.mutablecopy()
    headers[CORRELATION_ID_HEADER_NAME] = correlation_id
    request.scope.update(headers=headers.raw)
    # delete _headers to force update
    delattr(request, "_headers")
    log.info("Assigned %s as header correlation ID value.", correlation_id)


def get_validated_correlation_id(
    correlation_id: str, generate_correlation_id: bool
) -> str:
    """Returns valid correlation ID.

    If `correlation_id` is valid, it returns that.
    If it is empty and `generate_correlation_id` is True, a new value is generated.
    Otherwise, an error is raised.

    Raises:
        InvalidCorrelationIdError: If a correlation ID is invalid or empty (and
            `generate_correlation_id` is False).
    """
    if not correlation_id and generate_correlation_id:
        correlation_id = new_correlation_id()
        log.info("Generated new correlation id: %s", correlation_id)
    else:
        validate_correlation_id(correlation_id)
    return correlation_id


async def correlation_id_middleware(
    request: Request, call_next, generate_correlation_id: bool
):
    """Ensure request header has a valid correlation ID.

    Set the correlation ID ContextVar before passing on the request.

    Raises:
        InvalidCorrelationIdError: If a correlation ID is invalid or empty (and
            `generate_correlation_id` is False).
    """
    correlation_id = request.headers.get(CORRELATION_ID_HEADER_NAME, "")

    # Validate the correlation ID. If validation fails, return a Response with status 400.
    try:
        validated_correlation_id = get_validated_correlation_id(
            correlation_id, generate_correlation_id
        )
    except InvalidCorrelationIdError:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content="Correlation ID missing or invalid.",
        )

    # Update header if the validated value differs
    if validate_correlation_id != correlation_id:
        set_header_correlation_id(request, validated_correlation_id)

    # Set the correlation ID ContextVar
    async with set_correlation_id(validated_correlation_id):
        response = await call_next(request)
        return response


def configure_app(app: FastAPI, config: ApiConfigBase):
    """Configure a FastAPI app based on a config object."""
    app.root_path = config.api_root_path
    app.openapi_url = config.openapi_url
    app.docs_url = config.docs_url

    # configure CORS:
    kwargs: dict[str, Optional[Union[Sequence[str], bool]]] = {}
    if config.cors_allowed_origins is not None:
        kwargs["allow_origins"] = config.cors_allowed_origins
    if config.cors_allowed_headers is not None:
        kwargs["allow_headers"] = config.cors_allowed_headers
    if config.cors_allowed_methods is not None:
        kwargs["allow_methods"] = config.cors_allowed_methods
    if config.cors_allow_credentials is not None:
        kwargs["allow_credentials"] = config.cors_allow_credentials

    app.add_middleware(CORSMiddleware, **kwargs)
    app.add_middleware(
        BaseHTTPMiddleware,
        dispatch=partial(
            correlation_id_middleware,
            generate_correlation_id=config.generate_correlation_id,
        ),
    )

    # Configure the exception handler to issue error according to httpyexpect model:
    configure_exception_handler(app)


async def run_server(app: Union[FastAPI, str], config: ApiConfigBase):
    """Start backend server.

    In contrast to the behavior of `uvicorn.run`, it does not create a new asyncio event
    loop but uses the outer one.

    Args:
        app_import_path:
            Either a FastAPI app object (auto reload and multiple
            workers won't work) or the import path to the app object.
            The path follows the same style that is also used for
            the console_scripts in a setup.py/setup.cfg
            (see here for an example:
            from ghga_service_commons.api import run_server).
        config:
            A pydantic BaseSettings class that contains attributes "host" and "port".
    """
    uv_config = uvicorn.Config(
        app=app,
        host=config.host,
        port=config.port,
        log_config=None,
        reload=config.auto_reload,
        workers=config.workers,
    )

    server = uvicorn.Server(uv_config)
    try:
        await server.serve()
    except asyncio.CancelledError:
        if server.started:
            await server.shutdown()
        raise
