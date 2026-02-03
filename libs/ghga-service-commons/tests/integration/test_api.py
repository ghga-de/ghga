# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test api module."""

import asyncio
import multiprocessing
import re
import time

import httpx
import pytest
from fastapi import FastAPI

from ghga_service_commons.api import ApiConfigBase, run_server
from ghga_service_commons.api.api import configure_app
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.httpyexpect.server import HttpException
from ghga_service_commons.httpyexpect.server.handlers.fastapi_ import (
    configure_exception_handler,
)
from tests.integration.fixtures.hello_world_test_app import GREETING, app
from tests.integration.fixtures.utils import find_free_port

pytestmark = pytest.mark.asyncio()


async def test_run_server():
    """Test the run_server wrapper function."""
    config = ApiConfigBase()
    config.port = find_free_port()

    process = multiprocessing.Process(
        target=lambda: asyncio.run(run_server(app=app, config=config))
    )
    process.start()

    # give server time to come up:
    time.sleep(2)

    # run test query:
    try:
        response = httpx.get(f"http://{config.host}:{config.port}/greet")
    except Exception as exc:
        raise exc
    finally:
        process.kill()
    assert response.status_code == 200
    assert response.json() == GREETING


async def test_configure_cors_headers():
    """Test configuring the CORS headers."""
    # Configure the FastAPI app with nontrivial CORS settings
    cors_config = ApiConfigBase(
        cors_allowed_origins=["http://test.dev"],
        cors_allowed_methods=["GET"],
        cors_allowed_headers=["X-Custom-Request-Header"],
        cors_exposed_headers=["X-Custom-Response-Header"],
    )

    app = FastAPI()
    configure_app(app, cors_config)

    # Check that the app is configured properly
    client = AsyncTestClient(app)

    # Add a simple endpoint to test CORS
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    # Test preflight request
    response = await client.options(
        "/test",
        headers={
            "Origin": "http://test.dev",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Custom-Request-Header",
        },
    )

    # Verify CORS headers are set correctly
    assert response.status_code == 200
    headers = response.headers
    assert headers["access-control-allow-origin"] == "http://test.dev"
    assert headers["access-control-allow-methods"] == "GET"
    allow_headers = headers["access-control-allow-headers"].split(", ")
    assert "X-Custom-Request-Header" in allow_headers

    # Test actual request with CORS headers
    response = await client.get("/test", headers={"Origin": "http://test.dev"})

    assert response.status_code == 200
    headers = response.headers
    assert headers["access-control-allow-origin"] == "http://test.dev"
    expose_headers = headers["access-control-expose-headers"].split(", ")
    assert "X-Custom-Response-Header" in expose_headers


async def test_configure_exception_handler():
    """Test the exception handler configuration of a FastAPI app."""
    # example params for an http exception
    status_code = 400
    exception_id = "testException"
    description = "This is a test exception."
    data = {"test": "test"}

    # create a new FastAPI app and configure its exception handler:
    app = FastAPI()
    configure_exception_handler(app)

    # add a route function that raises an httpyexpect error:
    @app.get("/test")
    async def test_route():
        """A test route function raising an httpyexpect error."""
        raise HttpException(
            status_code=status_code,
            exception_id=exception_id,
            description=description,
            data=data,
        )

    # send a request using a test client:
    client = AsyncTestClient(app)
    response = await client.get("/test")

    # check if the response matches the expectation:
    assert response.status_code == status_code
    body = response.json()
    assert body["exception_id"] == exception_id
    assert body["description"] == description
    assert body["data"] == data


async def test_request_duration_log(caplog):
    """Check the middleware function that logs request duration in ms."""
    caplog.set_level("INFO")

    # small fastapi app with basic endpoint
    test_app = FastAPI()
    test_app.get("/")(lambda: 200)

    config = ApiConfigBase()
    configure_app(test_app, config)

    client = AsyncTestClient(test_app)
    await client.get("/")

    # Get list of the log messages
    for record in caplog.record_tuples:
        if record[0] == "ghga_service_commons.api.api":
            if re.match(r'GET http://.* "200 OK" - \d+ ms$', record[2]):
                break
    else:
        assert False, "Request duration log was not captured"
