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
#
"""Defines classes to set up mocked APIs for testing.

Different APIs should be set up using separate MockApi subclasses.
Overwritable handlers are defined in `on_*` attributes and are wired to their configured
path in the class `__init__` using `route`:

    class TestApiMock(MockApi):
        def __init__(self, base_url: str) -> None:
            super().__init__(base_url)
            self.on_delete_item: ResponseHandler = delete_item
            self.route("DELETE", "/items/{item_id}", "on_delete_item")

A test can change an endpoint response by overwriting the handler.
"""

import re
from collections.abc import Awaitable, Callable
from urllib.parse import unquote

import httpx2

__all__ = ["MockApi", "MockSetupError", "NotMockedError", "ResponseHandler"]

ResponseHandler = Callable[
    [httpx2.Request], httpx2.Response | Awaitable[httpx2.Response]
]

# Match what FastAPI considers a variable
_VARIABLE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")
_METHODS = ("GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE")


class MockSetupError(AssertionError):
    """Raise when a mock is set up wrong, as opposed to a failure of the code under test."""


class NotMockedError(Exception):
    """Raised when a route that no mock serves is requested.

    Test code that broadly catches `Exception` can check against a Mock's `requests` or `last_request`
    to assert that requests reached the API as expected.
    """


class MockApi:
    """Serves one mocked HTTP API at `base_url`.

    Subclasses have to set their `on_*` handlers and wire their routes to `__init__`.
    Every request a route serves is recorded in `requests` before its handler runs.
    """

    def __init__(self, base_url: str) -> None:
        self.base_url = httpx2.URL(base_url)
        if self.base_url.is_relative_url:
            raise MockSetupError(f"Base URL {base_url!r} needs a scheme and a host")
        if self.base_url.query:
            raise MockSetupError(
                f"Base URL {base_url!r} should not specify query parameters."
            )
        self.requests: list[httpx2.Request] = []
        self._routes: list[tuple[str, re.Pattern[str], str]] = []

    def route(self, method: str, path: str, handler: str) -> None:
        """Answer `method` requests to `path` with the handler in attribute `handler`.

        `path` is relative to the base URL.
        An empty path or `/` routes the base URL itself.

        Routes are tried in the order they were added, so a literal route needs to go before
        a variable one that would match. The other way round is refused.
        """
        method = method.upper()
        if method not in _METHODS:
            raise MockSetupError(f"Route method {method!r} is not an HTTP method")
        if not callable(getattr(self, handler, None)):
            raise MockSetupError(f"Handler `{handler}` is not defined.")
        if any(brace in part for part in _VARIABLE.split(path) for brace in "{}"):
            raise MockSetupError(
                f"Route path {path!r} contains braces outside a `{{variable}}`."
            )
        if "?" in path:
            raise MockSetupError(
                f"Route path {path!r} should not specify query parameters."
            )
        base_path = self.base_url.path.rstrip("/")
        regex = re.escape(base_path)
        if path.strip("/"):
            parts = _VARIABLE.split(path.lstrip("/"))
            regex += "/" + "[^/]+".join(re.escape(unquote(part)) for part in parts)
        else:
            regex += "/?"  # the base URL itself, with or without its trailing slash
        pattern = re.compile(regex)
        # A route without path variables is only allowed before an also matching route with path variables
        is_literal = not _VARIABLE.search(path)
        literal_path = f"{base_path}/{unquote(path.lstrip('/'))}"
        for routed_method, routed_pattern, routed_handler in self._routes:
            if routed_method == method and (
                routed_pattern == pattern
                or (is_literal and routed_pattern.fullmatch(literal_path))
            ):
                raise MockSetupError(
                    f"{method} {path!r} is registered for handler `{routed_handler}` already, so"
                    f" `{handler}` could never answer it"
                )
        self._routes.append((method, pattern, handler))

    @property
    def last_request(self) -> httpx2.Request | None:
        """The latest request a route of this mock served."""
        if not self.requests:
            return None
        return self.requests[-1]

    def _handler_for(self, request: httpx2.Request) -> ResponseHandler | None:
        """The current handler of the route serving `request`, if any."""
        url, base = request.url, self.base_url
        if (url.scheme, url.host, url.port) != (base.scheme, base.host, base.port):
            return None
        for method, pattern, handler in self._routes:
            if request.method == method and pattern.fullmatch(url.path):
                return getattr(self, handler)
        return None
