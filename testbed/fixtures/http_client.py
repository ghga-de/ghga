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
#

"""Fixture for testing code that uses HTTP requests."""

from base64 import b64encode
from collections.abc import Generator
from urllib.parse import urljoin, urlparse

from httpx import Client, HTTPStatusError, Response
from pytest import fixture

from fixtures.config import Config

__all__ = ["HttpClient", "Response", "http_fixture"]

TIMEOUT = 10  # timeout for HTTP requests in seconds

EXT_AUTH_APIS = ["ars", "dcs", "wps", "ums"]  # APIs that need ExtAuth
BASIC_AUTH_EXCLUDED_APIS = ["sms", "pcs", "dlq"]  # APIs that don't need BasicAuth


class HttpClient(Client):
    """An HTTP client that does not persist cookies."""

    def request(self, *args, **kwargs):
        """Build and send a request after clearing existing cookies.

        Since we set cookie headers manually in the tests
        and the HttpClient is also reused between tests,
        the cookie preservation feature of the default Client
        could give unexpected results, therefore we disable it.
        """
        self.cookies.clear()
        return super().request(*args, **kwargs)


@fixture(name="http", scope="session")
def http_fixture(config: Config) -> Generator[HttpClient, None, None]:
    """Pytest fixture for tests using an HTTP client."""
    black_box_mode = config.black_box_mode
    if black_box_mode:
        auth_basic = config.auth_basic
        if auth_basic:
            auth_basic = b64encode(auth_basic.encode("ascii")).decode("ascii")
            auth_basic = f"Basic {auth_basic}"
    else:
        auth_basic = None
    basic_auth_excluded_urls = tuple(
        getattr(config, f"{api}_url") for api in BASIC_AUTH_EXCLUDED_APIS
    )

    def request_hook(request):
        """HTTPX request hook for testing.

        This hook is called before sending the request.

        It adds Basic authentication if necessary,
        simulates the API gateway if we don't have one
        and logs the request on standard output.
        """
        url = str(request.url)
        headers = request.headers
        auth = headers.get("Authorization")
        session = headers.get("Cookie")

        if auth_basic and not url.startswith(basic_auth_excluded_urls):
            headers["Authorization"] = auth_basic
            auth_methods = "with basic"
            if auth:
                headers["X-Authorization"] = auth
                auth_methods += " and bearer"
            elif session:
                auth_methods += " and session"
        elif auth:
            auth_methods = "with bearer"
        elif session:
            auth_methods = "with session"
        else:
            auth_methods = "without"
        auth_methods += " auth"
        print(f"HTTP request: {request.method} {url} {auth_methods}")

    def response_hook(response):
        """HTTPX response hook for testing.

        This hook is called after receiving the response.

        It just logs the response status on standard output.
        """
        print(f"HTTP response status: {response.status_code}")

    hooks = {"request": [request_hook], "response": [response_hook]}

    with HttpClient(timeout=TIMEOUT, event_hooks=hooks) as client:
        yield client
