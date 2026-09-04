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
from typing import Any, Protocol, overload

import httpx2

from ghga_service_commons.api.mock_router import MockRouter
from ghga_service_commons.httpyexpect.server.exceptions import HttpException

__all__ = [
    "NO_BODY",
    "ApiMock",
    "Endpoint",
    "MockedEndpoint",
    "MonkeyPatch",
    "ResponseHandler",
    "RoutingTransport",
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
    network. For a client that also carries real traffic, or serves several APIs, mount
    a `RoutingTransport` instead.
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

    def patch_httpx_module(self, monkeypatch: MonkeyPatch) -> None:
        """Route the calls made through the `httpx2` module itself to this mock.

        Code building its own client, or calling `httpx2.get`, takes no transport and
        so cannot be pointed at a mock. This replaces those entry points for the test.
        """
        transport = self.as_transport()
        # bound before patching, so the replacements below don't call themselves
        real_client = httpx2.Client

        def mocked_client(**kwargs: Any) -> httpx2.Client:
            """Stand in for `httpx2.Client`, mounting the mock as its transport."""
            return real_client(transport=transport, **kwargs)

        def mocked_request(method: str, url: Any, **kwargs: Any) -> httpx2.Response:
            """Stand in for the module level request functions of `httpx2`.

            The arguments that only a client can take are passed to the one built here,
            the rest to the request it makes.
            """
            client_kwargs = {
                name: kwargs.pop(name)
                for name in ("cookies", "proxy", "trust_env", "verify")
                if name in kwargs
            }
            with mocked_client(**client_kwargs) as client:
                return client.request(method, url, **kwargs)

        monkeypatch.setattr(httpx2, "Client", mocked_client)
        for method in ("delete", "get", "head", "options", "patch", "post", "put"):
            monkeypatch.setattr(httpx2, method, partial(mocked_request, method.upper()))


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


class MonkeyPatch(Protocol):
    """The part of the pytest `monkeypatch` fixture that `ApiMock` uses."""

    def setattr(self, target: Any, name: Any, value: Any = ...) -> None:
        """Replace an attribute for the duration of the test."""


class RoutingTransport(httpx2.BaseTransport, httpx2.AsyncBaseTransport):
    """A transport serving each request from the mock whose base URL it matches.

    Mount it on a client that talks to several mocked APIs, or to a mocked API and the
    real network. Mocks are tried in the order given, and a request matching none of
    them raises. Pass a `fallback` transport to take those instead - an
    `httpx2.HTTPTransport()` or `httpx2.AsyncHTTPTransport()`, matching the kind of
    client in use, sends them out to the network.
    """

    def __init__(
        self,
        *mocks: ApiMock,
        fallback: httpx2.BaseTransport | httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        """Route to the given mocks, in the order they are passed."""
        # taken off the router rather than through `as_transport`, so that a mock
        # wrapping its own transport in one of these does not route into itself
        self._routes = [(mock.base_url, mock.router.as_transport()) for mock in mocks]
        self._fallback = fallback

    def _transport_for(
        self, request: httpx2.Request
    ) -> httpx2.BaseTransport | httpx2.AsyncBaseTransport:
        """Find the transport that may answer the given request."""
        url = str(request.url)
        for base_url, transport in self._routes:
            if url.startswith(base_url):
                return transport
        if self._fallback is None:
            raise AssertionError(f"Request to unmocked URL {url}")
        return self._fallback

    async def aclose(self) -> None:
        """Close the transport taking the requests that no mock claims."""
        if isinstance(self._fallback, httpx2.AsyncBaseTransport):
            await self._fallback.aclose()

    def close(self) -> None:
        """Close the transport taking the requests that no mock claims."""
        if isinstance(self._fallback, httpx2.BaseTransport):
            self._fallback.close()

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Dispatch a request made by an asynchronous client."""
        transport = self._transport_for(request)
        if not isinstance(transport, httpx2.AsyncBaseTransport):
            raise TypeError(f"{type(transport).__name__} cannot serve an async client")
        return await transport.handle_async_request(request)

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        """Dispatch a request made by a synchronous client."""
        transport = self._transport_for(request)
        if not isinstance(transport, httpx2.BaseTransport):
            raise TypeError(f"{type(transport).__name__} cannot serve a sync client")
        return transport.handle_request(request)


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
