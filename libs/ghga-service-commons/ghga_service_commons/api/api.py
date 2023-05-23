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

"""Functionality for initializing, configuring, and running RESTful
webapps with FastAPI"""

from typing import Dict, Optional, Sequence, Union

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpyexpect.server.handlers.fastapi_ import configure_exception_handler
from pydantic import BaseSettings, Field

try:  # workaround for https://github.com/pydantic/pydantic/issues/5821
    from typing_extensions import Literal
except ImportError:
    from typing import Literal  # type: ignore

# type alias for log level parameter
LogLevel = Literal["critical", "error", "warning", "info", "debug", "trace"]


class ApiConfigBase(BaseSettings):
    """A base class with API-required config params.
    Inherit your config class from this class if you need
    to run an API backend."""

    host: str = Field("127.0.0.1", description="IP of the host.")
    port: int = Field(
        8080, description="Port to expose the server on the specified host"
    )
    log_level: LogLevel = Field(
        "info", description="Controls the verbosity of the log."
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
        "/",
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
        example=["https://example.org", "https://www.example.org"],
        description=(
            "A list of origins that should be permitted to make cross-origin requests."
            + " By default, cross-origin requests are not allowed."
            + " You can use ['*'] to allow any origin."
        ),
    )
    cors_allow_credentials: Optional[bool] = Field(
        None,
        example=["https://example.org", "https://www.example.org"],
        description=(
            "Indicate that cookies should be supported for cross-origin requests."
            + " Defaults to False."
            + " Also, cors_allowed_origins cannot be set to ['*'] for credentials to be"
            + " allowed. The origins must be explicitly specified."
        ),
    )
    cors_allowed_methods: Optional[Sequence[str]] = Field(
        None,
        example=["*"],
        description=(
            "A list of HTTP methods that should be allowed for cross-origin requests."
            + " Defaults to ['GET']. You can use ['*'] to allow all standard methods."
        ),
    )
    cors_allowed_headers: Optional[Sequence[str]] = Field(
        None,
        example=[],
        description=(
            "A list of HTTP request headers that should be supported for cross-origin"
            + " requests. Defaults to []."
            + " You can use ['*'] to allow all headers."
            + " The Accept, Accept-Language, Content-Language and Content-Type headers"
            + " are always allowed for CORS requests."
        ),
    )


def configure_app(app: FastAPI, config: ApiConfigBase):
    """Configure a FastAPI app based on a config object."""

    app.root_path = config.api_root_path
    app.openapi_url = config.openapi_url
    app.docs_url = config.docs_url

    # configure CORS:
    kwargs: Dict[str, Optional[Union[Sequence[str], bool]]] = {}
    if config.cors_allowed_origins is not None:
        kwargs["allow_origins"] = config.cors_allowed_origins
    if config.cors_allowed_headers is not None:
        kwargs["allow_headers"] = config.cors_allowed_headers
    if config.cors_allowed_methods is not None:
        kwargs["allow_methods"] = config.cors_allowed_methods
    if config.cors_allow_credentials is not None:
        kwargs["allow_credentials"] = config.cors_allow_credentials

    app.add_middleware(CORSMiddleware, **kwargs)

    # Configure the exception handler to issue error according to httpyexpect model:
    configure_exception_handler(app)


async def run_server(app: Union[FastAPI, str], config: ApiConfigBase):
    """Starts backend server. In contrast to the behavior of `uvicorn.run`, it does not
    create a new asyncio event loop but uses the outer one.

    Args:
        app_import_path:
            Either a FastAPI app object (auto reload and multiple
            workers won't work) or the import path to the app object.
            The path follows the same style that is also used for
            the console_scripts in a setup.py/setup.cfg
            (see here for an example:
            from ghga_service_commons.api import run_server).
        config:
            A pydantic BaseSettings class that contains attributes
            "host", "port", and "log_level".
    """

    uv_config = uvicorn.Config(
        app=app,
        host=config.host,
        port=config.port,
        log_level=config.log_level,
        reload=config.auto_reload,
        workers=config.workers,
    )
    server = uvicorn.Server(uv_config)
    await server.serve()
