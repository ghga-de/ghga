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

"""Fixture for testing code that uses HTTP requests."""

from base64 import b64encode
from collections.abc import Generator

from httpx import Client as HttpClient
from httpx import Response
from pytest import fixture

from fixtures.config import Config

__all__ = ["http_fixture", "HttpClient", "Response"]

TIMEOUT = 10  # timeout for HTTP requests in seconds


@fixture(name="http", scope="session")
def http_fixture(config: Config) -> Generator[HttpClient, None, None]:
    """Pytest fixture for tests using an HTTP client."""
    if config.use_api_gateway:
        basic_auth = config.basic_auth_credentials
        if basic_auth:
            basic_auth = b64encode(basic_auth.encode("ascii")).decode("ascii")
            basic_auth = f"Basic {basic_auth}"
    else:
        basic_auth = None

    def request_hook(request):
        """Add Basic Authentication if necessary and log request."""
        headers = request.headers
        url = str(request.url)
        auth = headers.get("Authorization")
        if basic_auth:
            headers["Authorization"] = basic_auth
            auth_methods = "with basic"
            if auth:
                headers["X-Authorization"] = auth
                auth_methods += " and bearer"
        elif auth:
            auth_methods = "with bearer"
        else:
            auth_methods = "without"
        auth_methods += " auth"
        print(f"HTTP request: {request.method} {url} {auth_methods}")

    def response_hook(response):
        """Log response status."""
        print(f"HTTP response status: {response.status_code}")

    hooks = {"request": [request_hook], "response": [response_hook]}

    with HttpClient(timeout=TIMEOUT, event_hooks=hooks) as client:
        yield client
