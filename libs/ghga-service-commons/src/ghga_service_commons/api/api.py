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

"""Tools to setup and running FastAPI apps.

Contains functionality for initializing, configuring, and running
RESTful webapps with FastAPI.
"""

import asyncio
import http
import logging
import time
from collections.abc import Sequence

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from hexkit.correlation import (
    InvalidCorrelationIdError,
    correlation_id_from_str,
    new_correlation_id,
    set_correlation_id,
)
from pydantic import UUID4, Field
from pydantic_settings import BaseSettings

from ghga_service_commons.httpyexpect.models import HttpExceptionBody
from ghga_service_commons.httpyexpect.server.handlers.fastapi_ import (
    configure_exception_handler,
)

__all__ = [
    "CORRELATION_ID_HEADER_NAME",
    "ApiConfigBase",
    "UnexpectedCorrelationIdError",
    "configure_app",
    "get_validated_correlation_id",
    "run_server",
    "set_header_correlation_id",
]

# unofficial, but frequently used header name
# that is also used by Envoy-based proxies like Emissary-ingress
CORRELATION_ID_HEADER_NAME = "X-Request-Id"


log = logging.getLogger(__name__)


class ApiConfigBase(BaseSettings):
    """A base class with API-required config params.

    Inherit your config class from this class if you need
    to run an API backend.
    """

    host: str = Field(default="127.0.0.1", description="IP of the host.")
    port: int = Field(
        default=8080, description="Port to expose the server on the specified host"
    )
    auto_reload: bool = Field(
        default=False,
        description=(
            "A development feature."
            + " Set to `True` to automatically reload the server upon code changes"
        ),
    )
    workers: int = Field(default=1, description="Number of workers processes to run.")
    api_root_path: str = Field(
        default="",
        description=(
            "Root path at which the API is reachable."
            + " This is relative to the specified host and port."
        ),
    )
    openapi_url: str = Field(
        default="/openapi.json",
        description=(
            "Path to get the openapi specification in JSON format."
            + " This is relative to the specified host and port."
        ),
    )
    docs_url: str = Field(
        default="/docs",
        description=(
            "Path to host the swagger documentation."
            + " This is relative to the specified host and port."
        ),
    )

    # Starlette's defaults will only be overwritten if a
    # non-None value is specified:
    cors_allowed_origins: Sequence[str] | None = Field(
        default=None,
        examples=[["https://example.org", "https://www.example.org"]],
        description=(
            "A list of origins that should be permitted to make cross-origin requests."
            + " By default, cross-origin requests are not allowed."
            + " You can use ['*'] to allow any origin."
        ),
    )
    cors_allow_credentials: bool | None = Field(
        default=None,
        examples=[["https://example.org", "https://www.example.org"]],
        description=(
            "Indicate that cookies should be supported for cross-origin requests."
            + " Defaults to False."
            + " Also, cors_allowed_origins cannot be set to ['*'] for credentials to be"
            + " allowed. The origins must be explicitly specified."
        ),
    )
    cors_allowed_methods: Sequence[str] | None = Field(
        default=None,
        examples=[["*"]],
        description=(
            "A list of HTTP methods that should be allowed for cross-origin requests."
            + " Defaults to ['GET']. You can use ['*'] to allow all standard methods."
        ),
    )
    cors_allowed_headers: Sequence[str] | None = Field(
        default=None,
        examples=[[]],
        description=(
            "A list of HTTP request headers that should be supported for cross-origin"
            + " requests. Defaults to []."
            + " You can use ['*'] to allow all request headers."
            + " The Accept, Accept-Language, Content-Language, Content-Type and some"
            + " are always allowed for CORS requests."
        ),
    )
    cors_exposed_headers: Sequence[str] | None = Field(
        default=None,
        examples=[[]],
        description=(
            "A list of HTTP response headers that should be exposed for cross-origin"
            + " responses. Defaults to []."
            + " Note that you can NOT use ['*'] to expose all response headers."
            + " The Cache-Control, Content-Language, Content-Length, Content-Type, Expires,"
            + " Last-Modified and Pragma headers are always exposed for CORS responses."
        ),
    )
    generate_correlation_id: bool = Field(
        default=True,
        examples=[True, False],
        description=(
            "A flag, which, if False, will result in an error when inbound requests don't"
            + " possess a correlation ID. If True, requests without a correlation ID will"
            + " be assigned a newly generated ID in the correlation ID middleware function."
        ),
    )


def set_header_correlation_id(request: Request, correlation_id: UUID4):
    """Set the correlation ID on the request header. Modifies the header in-place."""
    headers = request.headers.mutablecopy()
    headers[CORRELATION_ID_HEADER_NAME] = str(correlation_id)
    request.scope.update(headers=headers.raw)
    # delete _headers to force update
    delattr(request, "_headers")
    log.debug("Assigned %s as header correlation ID value.", correlation_id)


def get_validated_correlation_id(
    correlation_id: str, generate_correlation_id: bool
) -> UUID4:
    """Returns valid correlation ID.

    If `correlation_id` is valid, it returns that.
    If it is empty/invalid and `generate_correlation_id` is True, a new value is generated.
    Otherwise, an error is raised.

    Raises:
        InvalidCorrelationIdError: If a correlation ID is invalid (and
            `generate_correlation_id` is False).
    """
    if not correlation_id and generate_correlation_id:
        valid_correlation_id = new_correlation_id()
        log.info("No correlation ID found. Generated new one: %s", correlation_id)
    else:
        try:
            valid_correlation_id = correlation_id_from_str(correlation_id)
        except InvalidCorrelationIdError:
            if generate_correlation_id:
                valid_correlation_id = new_correlation_id()
                log.warning(
                    "Detected a non-uuid4 value for correlation ID (%s). "
                    + "Replacing with newly-generated value: %s",
                    correlation_id,
                    valid_correlation_id,
                )
            else:
                raise
    return valid_correlation_id


class UnexpectedCorrelationIdError(RuntimeError):
    """Raised when the value of a response's correlation ID is unexpected."""

    def __init__(self, *, correlation_id: str):
        """Set the message and raise"""
        message = (
            f"Response contained unexpected correlation ID header: '{correlation_id}'"
        )
        super().__init__(message)


class CorrelationIdMiddleware:
    """ASGI middleware setting the correlation ID.

    The middleware sets the correlation ID ContextVar before processing the request.
    It makes sure the request headers either contain such an ID or generates one.
    It also ensures that the response headers contain the correlation ID.

    If a correlation ID is invalid or empty (and `generate_correlation_id` is False)
    then a "bad request" status is returned as an InvalidCorrelationIdError. If the
    correlation ID is already in the response headers, but the value is not what it
    should be, an UnexpectedCorrelationIdError is produced as an internal server error.
    """

    def __init__(self, app, generate_correlation_id: bool):
        """Initialize with the app."""
        self.app = app
        self.generate_correlation_id = generate_correlation_id

    async def __call__(self, scope, receive, send):
        """Process an ASGI connection."""
        if scope["type"] != "http":
            # Only process HTTP requests
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        headers = request.headers

        correlation_id_from_headers = headers.get(CORRELATION_ID_HEADER_NAME, "")

        # Validate the correlation ID.
        # If validation fails, create a response with bad request status.
        try:
            validated_correlation_id = get_validated_correlation_id(
                correlation_id_from_headers, self.generate_correlation_id
            )
        except InvalidCorrelationIdError as error:
            # report the plain error without any traceback
            await send(
                {
                    "type": "http.response.start",
                    "status": status.HTTP_400_BAD_REQUEST,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": HttpExceptionBody(
                        exception_id="invalidCorrelationId",
                        description=str(error),
                        data={},
                    )
                    .model_dump_json()
                    .encode("utf-8"),
                }
            )
            return

        # Update header if the validated value differs
        if str(validated_correlation_id) != correlation_id_from_headers:
            set_header_correlation_id(request, validated_correlation_id)

        async def send_wrapper(message):
            """Modify the response headers"""
            if message["type"] == "http.response.start":
                # Get the original response headers
                headers = message.setdefault("headers", [])
                header_name = CORRELATION_ID_HEADER_NAME.lower().encode()
                header_value = str(validated_correlation_id).encode()
                for header in headers:
                    key = header[0]
                    if key.lower() == header_name:
                        value = header[1]
                        if value != header_value:
                            # If the correlation ID is already set, but the value is
                            # different from what we expect, raise an error.
                            raise UnexpectedCorrelationIdError(correlation_id=value)
                headers.append((header_name, header_value))
            await send(message)

        # Set the correlation ID ContextVar
        async with set_correlation_id(validated_correlation_id):
            await self.app(scope, receive, send_wrapper)


class RequestLoggingMiddleware:
    """ASGI middleware that logs request processing times.

    Besides the processing time, it also logs the request method, URL as well as
    the response status code, so that this can replace the normal access logging.
    """

    def __init__(self, app):
        """Initialize with the app."""
        self.app = app

    async def __call__(self, scope, receive, send):
        """Process an ASGI connection."""
        if scope["type"] != "http":
            # Only process HTTP requests
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()

        request = Request(scope)
        url = request.url
        method = request.method

        # if no status code is produced, report an internal server error
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        async def send_wrapper(message):
            """Wrap the send function to capture the status code."""
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = int(round((time.perf_counter() - start_time) * 1000))  # noqa: RUF046
            try:
                status_phrase = http.HTTPStatus(status_code).phrase
            except ValueError:
                status_phrase = ""
            msg = f'{method} {url} "{status_code} {status_phrase}" - {duration} ms'
            extra = {
                "method": method,
                "url": str(url),
                "status_code": status_code,
                "duration_ms": duration,
            }
            log.info(msg, extra=extra)


def configure_app(app: FastAPI, config: ApiConfigBase):
    """Configure a FastAPI app based on a config object."""
    app.root_path = config.api_root_path.rstrip("/")
    app.openapi_url = config.openapi_url
    app.docs_url = config.docs_url

    # configure CORS:
    kwargs: dict[str, Sequence[str] | bool | None] = {}
    if config.cors_allowed_origins is not None:
        kwargs["allow_origins"] = config.cors_allowed_origins
    if config.cors_allowed_headers is not None:
        kwargs["allow_headers"] = config.cors_allowed_headers
    if config.cors_allowed_methods is not None:
        kwargs["allow_methods"] = config.cors_allowed_methods
    if config.cors_allow_credentials is not None:
        kwargs["allow_credentials"] = config.cors_allow_credentials
    if config.cors_exposed_headers is not None:
        kwargs["expose_headers"] = config.cors_exposed_headers

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware, config.generate_correlation_id)
    app.add_middleware(CORSMiddleware, **kwargs)  # type: ignore[arg-type]

    # Configure the exception handler to issue error according to httpyexpect model:
    configure_exception_handler(app)


async def run_server(app: FastAPI | str, config: ApiConfigBase):
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
        ws="websockets-sansio",
    )

    server = uvicorn.Server(uv_config)
    try:
        await server.serve()
    except asyncio.CancelledError:
        if server.started:
            await server.shutdown()
        raise
