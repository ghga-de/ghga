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

__all__ = [
    "MockApi",
    "MockSetupError",
    "NotMockedError",
    "ResponseHandler",
    "path_variables",
]

ResponseHandler = Callable[
    [httpx2.Request], httpx2.Response | Awaitable[httpx2.Response]
]

# Match what FastAPI considers a variable
_VARIABLE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")
# Stands in for a variable's value; a route path cannot contain a brace as a literal
_PROBE_SEGMENT = "{"
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
        A `{variable}` has to be a whole path segment.

        Routes are tried in the order they were added, so a route needs to go before a
        broader one that would match its requests too. The other way round is refused.
        """
        method = method.upper()
        if method not in _METHODS:
            raise MockSetupError(f"Route method {method!r} is not an HTTP method")
        if not callable(getattr(self, handler, None)):
            raise MockSetupError(f"Handler `{handler}` is not defined.")
        # Requests match on their decoded path, so the route path is decoded first
        decoded = unquote(path).lstrip("/")
        if any(brace in part for part in _VARIABLE.split(decoded) for brace in "{}"):
            raise MockSetupError(
                f"Route path {path!r} contains braces outside a `{{variable}}`."
            )
        if any(
            _VARIABLE.search(segment) and not _VARIABLE.fullmatch(segment)
            for segment in decoded.split("/")
        ):
            raise MockSetupError(
                f"Route path {path!r} has a variable that is not a whole path segment."
            )
        if "?" in path:  # as written, since an encoded `?` is part of the path
            raise MockSetupError(
                f"Route path {path!r} should not specify query parameters."
            )
        base_path = self.base_url.path.rstrip("/")
        regex = re.escape(base_path)
        if decoded.strip("/"):
            parts = _VARIABLE.split(decoded)
            regex += "/" + "[^/]+".join(re.escape(part) for part in parts)
        else:
            regex += "/?"  # the base URL itself, with or without its trailing slash
        pattern = re.compile(regex)
        # A route must be defined above a broader one that matches its requests too.
        probe_path = f"{base_path}/{_VARIABLE.sub(_PROBE_SEGMENT, decoded)}"
        for routed_method, routed_pattern, routed_handler in self._routes:
            if routed_method == method and (
                routed_pattern == pattern or routed_pattern.fullmatch(probe_path)
            ):
                raise MockSetupError(
                    f"{method} {path!r} is registered for handler `{routed_handler}` already, so"
                    f" `{handler}` could never answer it"
                )
        self._routes.append((method, pattern, handler))

    @property
    def last_request(self) -> httpx2.Request | None:
        """The latest request served by this mock."""
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


def path_variables(request: httpx2.Request, path: str) -> dict[str, str]:
    """Read the `{variable}` values of route `path` from the end of the request's path.

    `path` is the one given to `route`, so a handler can look up what its route matched.
    """
    decoded = unquote(path).lstrip("/")
    names = [variable[1:-1] for variable in _VARIABLE.findall(decoded)]
    if decoded.strip("/"):
        parts = _VARIABLE.split(decoded)
        regex = "/" + "([^/]+)".join(re.escape(part) for part in parts)
    else:
        regex = "/?"  # the base URL itself, which has no variables
    match = re.search(f"{regex}$", request.url.path)
    if match is None:
        raise MockSetupError(
            f"Request path {request.url.path!r} does not end in route path {path!r}."
        )
    return dict(zip(names, match.groups(), strict=True))
