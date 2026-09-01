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
"""Mocks of the HTTP APIs a service calls, built on top of `MockRouter`.

Declare an API's endpoints and their default answers once:
```
class EkssApiMock(ApiMock):
    on_get_envelope = endpoint("GET", "/secrets/{secret_id}/envelopes", respond(200))
    on_delete_secret = endpoint("DELETE", "/secrets/{secret_id}", respond(204))
```
A test then overrides only what it cares about:
```
ekss.on_delete_secret = respond(500)
```
Any callable works as a handler: it takes the request plus the path variables as
keyword arguments and returns a response. Every request lands in the mock's `requests`,
so assert on those after the call under test, not inside a handler.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from functools import partial
from json import dumps as json_dumps
from typing import Any, overload

import httpx2

from ghga_service_commons.api.mock_router import MockRouter
from ghga_service_commons.httpyexpect.server.exceptions import HttpException

__all__ = [
    "NO_BODY",
    "ApiMock",
    "Endpoint",
    "MockedEndpoint",
    "ResponseHandler",
    "endpoint",
    "fail_to_connect",
    "fail_with",
    "httpyexpect_body",
    "httpyexpect_error_handler",
    "in_sequence",
    "respond",
    "unconfigured",
]

# Takes the request and the path variables as keyword arguments. An `async` handler
# needs an async client.
ResponseHandler = Callable[..., "httpx2.Response | Awaitable[httpx2.Response]"]


# Used to tell "no body" apart from a JSON `null`, which httpx2 cannot.
class _NoBody:
    """The type of the `NO_BODY` marker."""

    def __repr__(self) -> str:
        """Show the marker by its exported name."""
        return "NO_BODY"


NO_BODY: Any = _NoBody()


class ApiMock:
    """A mock of one HTTP API's endpoints, answering requests without hitting the network.

    Derive from this class and declare the endpoints with `endpoint(...)`, or register
    one-off ones with `add()`. A request matching none of them gets a 404, never the
    network.
    """

    def __init__(self, *, base_url: str = "", router: MockRouter | None = None) -> None:
        """Serve the API at `base_url` from `router`.

        Without a `base_url`, endpoint paths match the end of any request URL. Mocks
        sharing a `router` share one transport, but record separately.
        """
        self.base_url = _normalize_base_url(base_url)
        self.requests: list[httpx2.Request] = []
        self.router: MockRouter = MockRouter() if router is None else router

        for declared in _declared_endpoints(type(self)):
            self._register(
                declared.method,
                declared.path,
                partial(declared.handler_for, self),
            )

    def _register(
        self, method: str, path: str, handler_of: Callable[[], ResponseHandler]
    ) -> None:
        """Register an endpoint answering with whatever `handler_of` returns.

        Looked up per request, so a newly assigned handler takes effect at once.
        """

        def endpoint_function(
            request: httpx2.Request, **path_variables: str
        ) -> httpx2.Response | Awaitable[httpx2.Response]:
            """Record the request and let the current handler answer it."""
            self.requests.append(request)
            return handler_of()(request, **path_variables)

        # dynamically register a function on the provided router
        register = getattr(self.router, method.lower())
        register(re.escape(self.base_url) + path)(endpoint_function)

    def add(
        self, *, method: str, path: str, handler: ResponseHandler | None = None
    ) -> MockedEndpoint:
        """Create and register an endpoint under `method` and `path` and return it.

        `path` is relative to the base URL. The default handler answers with a 200.
        """
        mocked_endpoint = MockedEndpoint(handler or respond())
        self._register(method, path, lambda: mocked_endpoint)
        return mocked_endpoint

    def as_transport(self) -> httpx2.MockTransport:
        """Return a transport that answers from this mock."""
        return self.router.as_transport()

    @property
    def last_request(self) -> httpx2.Request:
        """The most recent request that reached this mock."""
        if not self.requests:
            raise AssertionError(f"No request reached the {type(self).__name__}")
        return self.requests[-1]


class Endpoint:
    """One endpoint of an API, declared in the class body of an `ApiMock`.

    The attribute it is assigned to holds the handler answering it, starting at
    `default` - or, without one, at a handler that refuses rather than inventing a
    response. `path` is relative to the mock's base URL, and its `{variable}`
    placeholders reach the handler as keyword arguments.
    """

    def __init__(
        self, method: str, path: str, default: ResponseHandler | None = None
    ) -> None:
        """Declare an endpoint served under `path`, answering with `default`."""
        self.method = method.upper()
        self.path = path
        self.name = ""
        self._declared_default = default
        # replaced once `__set_name__` supplies the attribute name
        self.default: ResponseHandler = unconfigured("Unconfigured endpoint")

    def __set_name__(self, owner: type, name: str) -> None:
        """Learn the attribute name this was assigned to."""
        self.name = name
        self.default = self._declared_default or unconfigured(name)

    # Overloads needed right now for type checking in existing code, can be removed once lib/tool/service changes are merged
    @overload
    def __get__(self, obj: None, objtype: type | None = None) -> Endpoint: ...

    @overload
    def __get__(self, obj: ApiMock, objtype: type | None = None) -> ResponseHandler: ...

    def __get__(
        self, obj: ApiMock | None, objtype: type | None = None
    ) -> Endpoint | ResponseHandler:
        """Get the handler answering this endpoint."""
        return self if obj is None else self.handler_for(obj)

    def __set__(self, obj: ApiMock, handler: ResponseHandler) -> None:
        """Answer with `handler` from now on."""
        obj.__dict__[self.name] = handler

    def handler_for(self, obj: ApiMock) -> ResponseHandler:
        """Get the handler `obj` answers this endpoint with."""
        handler: ResponseHandler = obj.__dict__.get(self.name, self.default)
        return handler


class MockedEndpoint:
    """A single mocked endpoint that records the requests it receives.

    Reassign `handler` to change how it answers the calls that follow.
    """

    def __init__(self, handler: ResponseHandler) -> None:
        """Start out answering with `handler`."""
        self.handler = handler
        self.requests: list[httpx2.Request] = []

    def __call__(
        self, request: httpx2.Request, **path_variables: str
    ) -> httpx2.Response | Awaitable[httpx2.Response]:
        """Record the request and let the current handler answer it."""
        self.requests.append(request)
        return self.handler(request, **path_variables)

    @property
    def call_count(self) -> int:
        """The number of requests that reached this endpoint."""
        return len(self.requests)


def _declared_endpoints(mock_class: type) -> list[Endpoint]:
    """Collect the endpoints declared in a mock class and its base classes.

    Base classes come first, and a redeclared endpoint replaces the one it overrides.
    """
    endpoints: dict[str, Endpoint] = {}
    for mock_classes in reversed(mock_class.__mro__):
        for name, attribute in vars(mock_classes).items():
            if isinstance(attribute, Endpoint):
                endpoints[name] = attribute
    return list(endpoints.values())


def _normalize_base_url(base_url: str) -> str:
    """Bring a base URL into the spelling that request URLs are compared against."""
    if not base_url:
        return ""
    url = httpx2.URL(base_url).copy_with(query=None, fragment=None)
    return str(url).rstrip("/")


def endpoint(
    method: str, path: str, default: ResponseHandler | None = None
) -> Endpoint:
    """Declare an endpoint of an `ApiMock`. See `Endpoint`."""
    return Endpoint(method, path, default)


def fail_to_connect(reason: str = "All connection attempts failed") -> ResponseHandler:
    """Make a handler that simulates the API being unreachable."""

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Refuse the connection."""
        raise httpx2.ConnectError(reason, request=request)

    return handler


def fail_with(error: Exception) -> ResponseHandler:
    """Make a handler that raises `error` instead of answering.

    For `httpx2.RequestError` subclasses the client attaches the offending request on
    the way out.
    """

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Raise instead of answering."""
        raise error

    return handler


def httpyexpect_error_handler(
    request: httpx2.Request, exception: HttpException
) -> httpx2.Response:
    """Custom error handler for httpyexpect types.

    `MockRouter` raises for an unmatched request or an uncastable path variable.
    Pass this to the router so those reach the service's error handling as responses:
    ```
    MockRouter(
        exception_handler=httpyexpect_error_handler,
        exceptions_to_handle=(HttpException,),
    )
    ```
    """
    body = httpyexpect_body(
        exception.body.exception_id, exception.body.description, exception.body.data
    )
    # serialized leniently, because `data` does not always hold plain JSON: the 422 the
    # router raises for an uncastable path variable reports the type it tried to cast to
    return httpx2.Response(
        exception.status_code,
        content=json_dumps(body, default=str),
        headers={"content-type": "application/json"},
    )


def httpyexpect_body(
    exception_id: str, description: str = "", data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the body of a httpyexpect response."""
    return {
        "exception_id": exception_id,
        "description": description,
        "data": data or {},
    }


def in_sequence(*handlers: ResponseHandler) -> ResponseHandler:
    """Build a handler that answers consecutive requests with `handlers`, in order.

    A request past the last handler is an error, so use this only where the number of
    requests is part of the assertion.
    """
    remaining = list(handlers)

    def handler(
        request: httpx2.Request, **path_variables: str
    ) -> httpx2.Response | Awaitable[httpx2.Response]:
        """Answer with the next handler in line."""
        if not remaining:
            raise AssertionError(f"Unexpected additional request to {request.url}")
        return remaining.pop(0)(request, **path_variables)

    return handler


def respond(
    status_code: int = 200,
    *,
    json: Any = NO_BODY,
    content: bytes | str | None = None,
    headers: dict[str, str] | None = None,
) -> ResponseHandler:
    """Build a handler that always answers the same way.

    `json` sets a JSON body, `json=None` is a JSON `null`, while leaving it
    out means no body, unless `content` is given.
    """

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Answer with the canned response."""
        if json is NO_BODY:
            return httpx2.Response(status_code, content=content, headers=headers)
        if json is None:
            # httpx2 would read this as no body, so encode `null` by hand
            return httpx2.Response(
                status_code,
                content=b"null",
                headers={"content-type": "application/json", **(headers or {})},
            )
        return httpx2.Response(status_code, json=json, headers=headers)

    return handler


def unconfigured(name: str) -> ResponseHandler:
    """Build a handler for an endpoint no test has assigned a response to."""

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Refuse to make up a response."""
        raise AssertionError(
            f"Unexpected request to {request.url}. Assign a handler to"
            + f" `{name}` if the test is meant to call this endpoint."
        )

    return handler
