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
            self.on_delete_item: ResponseHandler = respond(204)
            self.route("DELETE", "/items/{item_id}", "on_delete_item")

A test can change an endpoint response by overwriting the handler:

    test_api = TestApiMock(config.test_api_url)
    test_api.on_delete_item = respond(404)
    client = httpx2.AsyncClient(transport=test_api.as_transport())

`serve` puts several mocks behind one client.
A request that no route serves raises `NotMockedError`.
"""

import copy
import re
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any
from urllib.parse import unquote

import httpcore2
import httpx2

__all__ = [
    "MockApi",
    "MockSetupError",
    "NotMockedError",
    "ResponseHandler",
    "fail_to_connect",
    "instrumentable",
    "respond",
    "serve",
]

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

    def as_transport(self) -> httpx2.MockTransport:
        """A transport answering from this mock, for sync and async clients."""
        return serve(self)

    def _handler_for(self, request: httpx2.Request) -> ResponseHandler | None:
        """The current handler of the route serving `request`, if any."""
        url, base = request.url, self.base_url
        if (url.scheme, url.host, url.port) != (base.scheme, base.host, base.port):
            return None
        for method, pattern, handler in self._routes:
            if request.method == method and pattern.fullmatch(url.path):
                return getattr(self, handler)
        return None


def serve(*mocks: MockApi) -> httpx2.MockTransport:
    """Create a transport answering from one or multiple `mocks`, for sync and async clients.

    A request hits the first matching mock that contains a route for it.
    """

    def answer(request: httpx2.Request) -> Any:
        for mock in mocks:
            handler = mock._handler_for(request)
            if handler is not None:
                mock.requests.append(request)
                return handler(request)
        raise NotMockedError(f"No mock serves {request.method} {request.url}")

    return _MockTransport(answer)


class _MockTransport(httpx2.MockTransport):
    """Custom flavour of a MockTransport with some special handling for the mock setup."""

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        """Answer a sync client, which cannot await an async handler's answer."""
        request.read()
        response = self.handler(request)
        if isinstance(response, Awaitable):
            if isinstance(response, Coroutine):
                response.close()  # nothing will await it, so Python would warn
            raise MockSetupError(
                f"The handler answering {request.method} {request.url} is async, but"
                " the call was made by a synchronous client. Use an async client, or a"
                " handler that is not async."
            )
        return _answered(response, request)

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Answer an async client, awaiting the answer of an async handler."""
        await request.aread()
        response = self.handler(request)
        if isinstance(response, Awaitable):
            response = await response
        return _answered(response, request)


def _answered(response: object, request: httpx2.Request) -> httpx2.Response:
    """Returns the response a handler answered `request` with."""
    if not isinstance(response, httpx2.Response):
        raise MockSetupError(
            f"The handler answering {request.method} {request.url} returned"
            f" {type(response).__name__}, not an httpx2.Response"
        )
    return response


def instrumentable(transport: httpx2.MockTransport) -> httpx2.AsyncHTTPTransport:
    """Wrapper for transports to correctly deal with non-test code instrumentation.

    This is needed to correctly record OTel spans in tests that use the custom mock transports.
    """
    wrapped = httpx2.AsyncHTTPTransport()
    wrapped._pool = _MockPool(transport)  # type: ignore[assignment]
    return wrapped


class _MockPool:
    """Stand-in for httpcore2's connection pool, answering from a mock transport."""

    def __init__(self, transport: httpx2.MockTransport) -> None:
        self._transport = transport

    async def handle_async_request(
        self, request: httpcore2.Request
    ) -> httpcore2.Response:
        """Rebuild `request` for httpx2, answer it, and hand the answer back."""
        stream: Any = request.stream
        body = b"".join([chunk async for chunk in stream])
        url = request.url
        rebuilt = httpx2.Request(
            request.method.decode(),
            httpx2.URL(
                scheme=url.scheme.decode(),
                host=url.host.decode(),
                port=url.port,
                raw_path=url.target,
            ),
            headers=request.headers,
            content=body,
            extensions=request.extensions,
        )
        response = await self._transport.handle_async_request(rebuilt)
        # Passed on still encoded, as its Content-Encoding header says
        raw: Any = response.stream
        content = b"".join([chunk async for chunk in raw])
        return httpcore2.Response(
            response.status_code, headers=response.headers.raw, content=content
        )

    async def __aenter__(self) -> "_MockPool":
        """Enter as httpx2's transport enters its pool."""
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Leave as httpx2's transport leaves its pool."""

    async def aclose(self) -> None:
        """Nothing to close: no connections were opened."""


def respond(
    status_code: int = 200,
    *,
    json: Any = None,
    content: bytes | str | None = None,
    headers: dict[str, str] | None = None,
) -> ResponseHandler:
    """Create a handler answering every request with the configured response."""
    if json is not None and content is not None:
        raise MockSetupError(
            "respond() takes `json` or `content` as the body, not both"
        )
    # deepcopy, so handler changes don't cause unexpected side effects
    json = copy.deepcopy(json)
    headers = dict(headers) if headers is not None else None

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status_code, json=json, content=content, headers=headers)

    return handler


def fail_to_connect(reason: str = "All connection attempts failed") -> ResponseHandler:
    """Create a handler making the API look unreachable."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError(reason, request=request)

    return handler
