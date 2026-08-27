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

An API is modeled once, by a class declaring each of its endpoints and how that endpoint
answers when a test says nothing about it:
```
class EkssApiMock(ApiMock):
    on_get_envelope = endpoint("GET", "/secrets/{secret_id}/envelopes", respond(200))
    on_delete_secret = endpoint("DELETE", "/secrets/{secret_id}", respond(204))
```
A test then states only what it cares about, and inherits the defaults for the rest:
```
ekss.on_delete_secret = respond(500)
```
Anything assignable to an `on_...` attribute works, not just the handlers in this
module: a handler is any callable taking the request, plus the endpoint's path variables
as keyword arguments, and returning a response. It may be `async`, in which case the
mock can only be used from an async client.

Every request that reaches a mock is recorded in its `requests`, so assertions about
what the service sent belong after the call under test, not inside a handler where a
failure would surface as a request error.

For the endpoints that are not worth modeling - a one-off in a single test - `ApiMock`
can also be used directly and its endpoints registered with `add()`.
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

# A handler answers one request. It is passed the request and, as keyword arguments, the
# path variables of the endpoint it is registered on, so it can ignore either. Handlers
# may be `async`, in which case only an async client can drive the mock.
ResponseHandler = Callable[..., "httpx2.Response | Awaitable[httpx2.Response]"]


class _NoBody:
    """The type of the `NO_BODY` marker."""

    def __repr__(self) -> str:
        """Show the marker under the name it is exported as."""
        return "NO_BODY"


# Marker distinguishing "no body at all" from a JSON body of `null`, which httpx2 itself
# cannot tell apart: it reads `json=None` as the former.
NO_BODY: Any = _NoBody()


def respond(
    status_code: int = 200,
    *,
    json: Any = NO_BODY,
    content: bytes | str | None = None,
    headers: dict[str, str] | None = None,
) -> ResponseHandler:
    """Make a handler that always answers with the same status code and body.

    Passing `json` gives the response a JSON body, `json=None` included - that is the
    JSON value `null`. Leaving `json` out means no body at all, unless `content` is
    given, which is sent as it is.
    """

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Answer with the canned response."""
        if json is NO_BODY:
            return httpx2.Response(status_code, content=content, headers=headers)
        if json is None:
            # httpx2 reads `json=None` as "no body", so `null` is encoded here instead
            return httpx2.Response(
                status_code,
                content=b"null",
                headers={"content-type": "application/json", **(headers or {})},
            )
        return httpx2.Response(status_code, json=json, headers=headers)

    return handler


def fail_with(error: Exception) -> ResponseHandler:
    """Make a handler that raises `error` instead of answering.

    Used to simulate transport level failures. For `httpx2.RequestError` subclasses the
    client attaches the offending request to the exception on its way out.
    """

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Raise instead of answering."""
        raise error

    return handler


def fail_to_connect(reason: str = "All connection attempts failed") -> ResponseHandler:
    """Make a handler that simulates the API being unreachable."""

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Refuse the connection."""
        raise httpx2.ConnectError(reason, request=request)

    return handler


def in_sequence(*handlers: ResponseHandler) -> ResponseHandler:
    """Make a handler that answers consecutive requests with `handlers`, in order.

    Once the handlers are used up, any further request is an error - use this only
    where the exact number of requests is part of what the test asserts.
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


def unconfigured(name: str) -> ResponseHandler:
    """Make a handler for an endpoint that the test has not assigned a response to."""

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Refuse to make up a response."""
        raise AssertionError(
            f"Unexpected request to {request.url}. Assign a handler to"
            + f" `{name}` if the test is meant to call this endpoint."
        )

    return handler


def httpyexpect_body(
    exception_id: str, description: str = "", data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the body a GHGA service sends for an error, in the httpyexpect schema.

    Pass it to `respond` to have an endpoint answer with such an error:
    ```
    ekss.on_get_envelope = respond(404, json=httpyexpect_body("secretNotFoundError"))
    ```
    """
    return {
        "exception_id": exception_id,
        "description": description,
        "data": data or {},
    }


def httpyexpect_error_handler(
    request: httpx2.Request, exception: HttpException
) -> httpx2.Response:
    """Answer with an `HttpException` rather than letting it propagate.

    `MockRouter` raises one when no endpoint matches a request, or when a path variable
    doesn't fit the type its endpoint declares. Pass this to the router to have those
    turned into responses, so an unmocked call reaches the service's own error handling
    instead of the exception surfacing straight out of the transport:
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


class MockedEndpoint:
    """A single mocked endpoint that records the requests it receives.

    Responses come from `handler`, which tests can reassign at any point to change how
    the endpoint answers the calls that follow.
    """

    def __init__(self, handler: ResponseHandler) -> None:
        """Start out answering with the given handler."""
        self.handler = handler
        self.requests: list[httpx2.Request] = []

    def __call__(
        self, request: httpx2.Request, **path_variables: str
    ) -> httpx2.Response | Awaitable[httpx2.Response]:
        """Record the request and let the currently assigned handler answer it."""
        self.requests.append(request)
        return self.handler(request, **path_variables)

    @property
    def call_count(self) -> int:
        """The number of requests that reached this endpoint."""
        return len(self.requests)


class Endpoint:
    """One endpoint of an API, declared in the class body of an `ApiMock`.

    The attribute it is assigned to holds the handler that currently answers the
    endpoint, starting out as `default` - or, when no default is given, as a handler
    refusing to make up a response, so that a test never gets one by accident.

    `path` is relative to the base URL of the mock it belongs to, and may contain
    `{variable}` placeholders, which are passed to the handler as keyword arguments.
    """

    def __init__(
        self, method: str, path: str, default: ResponseHandler | None = None
    ) -> None:
        """Declare an endpoint served under `path`, answering with `default`."""
        self.method = method.upper()
        self.path = path
        self.name = ""
        self._declared_default = default
        # stands in until `__set_name__` can name the attribute to assign a handler to
        self.default: ResponseHandler = unconfigured("this endpoint")

    def __set_name__(self, owner: type, name: str) -> None:
        """Learn the name of the attribute this endpoint was assigned to."""
        self.name = name
        self.default = self._declared_default or unconfigured(name)

    @overload
    def __get__(self, obj: None, objtype: type | None = None) -> Endpoint: ...

    @overload
    def __get__(self, obj: ApiMock, objtype: type | None = None) -> ResponseHandler: ...

    def __get__(
        self, obj: ApiMock | None, objtype: type | None = None
    ) -> Endpoint | ResponseHandler:
        """Get the handler currently answering this endpoint."""
        return self if obj is None else self.handler_for(obj)

    def __set__(self, obj: ApiMock, handler: ResponseHandler) -> None:
        """Have this endpoint answer with the given handler from now on."""
        obj.__dict__[self.name] = handler

    def handler_for(self, obj: ApiMock) -> ResponseHandler:
        """Get the handler that the given mock currently answers this endpoint with."""
        handler: ResponseHandler = obj.__dict__.get(self.name, self.default)
        return handler


def endpoint(
    method: str, path: str, default: ResponseHandler | None = None
) -> Endpoint:
    """Declare an endpoint of an `ApiMock`. See `Endpoint`."""
    return Endpoint(method, path, default)


def _normalize_base_url(base_url: str) -> str:
    """Bring a base URL into the spelling that request URLs are compared against."""
    if not base_url:
        return ""
    url = httpx2.URL(base_url).copy_with(query=None, fragment=None)
    return str(url).rstrip("/")


def _declared_endpoints(mock_class: type) -> list[Endpoint]:
    """Collect the endpoints declared in a mock class and the classes it derives from.

    Base classes come first, and an endpoint redeclared in a subclass replaces the one
    it overrides rather than being registered next to it.
    """
    endpoints: dict[str, Endpoint] = {}
    for klass in reversed(mock_class.__mro__):
        for name, attribute in vars(klass).items():
            if isinstance(attribute, Endpoint):
                endpoints[name] = attribute
    return list(endpoints.values())


class MonkeyPatch(Protocol):
    """The part of the pytest `monkeypatch` fixture that `ApiMock` uses."""

    def setattr(self, target: Any, name: Any, value: Any = ...) -> None:
        """Replace an attribute for the duration of the test."""
        ...


class ApiMock:
    """A mock of the endpoints of one HTTP API, answering requests without a network.

    Model an API by deriving from this class and declaring its endpoints with
    `endpoint(...)`; register the one-off endpoints of a single test with `add()`.

    The transport returned by `as_transport()` answers *every* request, so a test using
    it cannot accidentally reach the network - a URL that matches no registered endpoint
    gets a 404 from the router rather than being sent out. Where the same client also
    has to carry real traffic, or requests for several APIs, mount a `RoutingTransport`
    instead.
    """

    def __init__(self, *, base_url: str = "", router: MockRouter | None = None) -> None:
        """Serve the API at `base_url` from `router`.

        Endpoints are registered relative to `base_url`, and only requests going to it
        are answered. Leaving it out means matching the endpoint paths against the end
        of the request URLs instead, wherever they are addressed to.

        Pass a `router` to have several mocks share one, and hence one transport. Each
        of them still records only the requests to its own endpoints.
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

    @property
    def last_request(self) -> httpx2.Request:
        """The most recent request that reached this mock."""
        if not self.requests:
            raise AssertionError(f"No request reached the {type(self).__name__}")
        return self.requests[-1]

    def add(
        self, *, method: str, path: str, handler: ResponseHandler | None = None
    ) -> MockedEndpoint:
        """Register an endpoint under `method` and `path` and return it.

        `path` is relative to the base URL of this mock, and defaults to answering with
        a bare 200 response. Use this for the endpoints of a single test; the ones an
        API always serves are better declared with `endpoint(...)`.
        """
        mocked_endpoint = MockedEndpoint(handler or respond())
        self._register(method, path, lambda: mocked_endpoint)
        return mocked_endpoint

    def as_transport(self) -> httpx2.MockTransport:
        """Return a transport answering this API's requests with this mock."""
        return self.router.as_transport()

    def patch_httpx_module(self, monkeypatch: MonkeyPatch) -> None:
        """Route the calls made through the `httpx2` module itself to this mock.

        Code that builds its own client, or calls `httpx2.get` and friends, takes no
        transport and so cannot be pointed at a mock from the outside. This replaces
        those module level entry points for the duration of the test.
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

    def _register(
        self, method: str, path: str, handler_of: Callable[[], ResponseHandler]
    ) -> None:
        """Register an endpoint answering with whatever `handler_of` returns.

        The handler is looked up per request rather than bound here, so that assigning
        a new one takes effect for the calls that follow.
        """

        def endpoint_function(
            request: httpx2.Request, **path_variables: str
        ) -> httpx2.Response | Awaitable[httpx2.Response]:
            """Record the request and let the currently assigned handler answer it."""
            self.requests.append(request)
            return handler_of()(request, **path_variables)

        register = getattr(self.router, method.lower())
        register(re.escape(self.base_url) + path)(endpoint_function)


class RoutingTransport(httpx2.BaseTransport, httpx2.AsyncBaseTransport):
    """Hands each request to the mock of the API it is addressed to.

    Requests that no mock claims are refused, unless a `fallback` transport is given to
    take them - `httpx2.AsyncHTTPTransport()` to let them out to the network as usual,
    or a transport of your own to decide per request.
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

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        """Dispatch a request made by a synchronous client."""
        transport = self._transport_for(request)
        if not isinstance(transport, httpx2.BaseTransport):
            raise TypeError(f"{type(transport).__name__} cannot serve a sync client")
        return transport.handle_request(request)

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Dispatch a request made by an asynchronous client."""
        transport = self._transport_for(request)
        if not isinstance(transport, httpx2.AsyncBaseTransport):
            raise TypeError(f"{type(transport).__name__} cannot serve an async client")
        return await transport.handle_async_request(request)

    def close(self) -> None:
        """Close the transport taking the requests that no mock claims."""
        if isinstance(self._fallback, httpx2.BaseTransport):
            self._fallback.close()

    async def aclose(self) -> None:
        """Close the transport taking the requests that no mock claims."""
        if isinstance(self._fallback, httpx2.AsyncBaseTransport):
            await self._fallback.aclose()

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
