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
"""Mocks of the HTTP APIs a service calls.

Model an API once, with the URL it is served at and the endpoints it answers:
```
class MockedThingsApi(MockedApi):
    base_url = "http://things.test/api"

    # answers out of the mock's own state, so it is bound like a method via decorator
    @endpoint("GET", "/things/{thing_id}")
    def on_get_thing(self, request, *, thing_id: UUID) -> httpx2.Response:
        return httpx2.Response(200, json=self.things[thing_id])

    # answers the same way every time, so it takes no `self`
    on_delete_thing = endpoint("DELETE", "/things/{thing_id}", respond(204))
```
A `{variable}` reaches the handler as the parameter of that name, cast to whatever that
parameter is annotated with, and matches one path segment unless it names a converter,
as in `{file_path:path}`.

A test overrides what it cares about with `things.on_delete_thing = respond(500)`, then
serves the mocks one of two ways. Where the code under test takes a transport, hand it
one, and only the clients built with it are mocked:
```
prepare_thing(config, base_transport=things.as_transport())
```
Where it does not, a `MockedApis` block intercepts `httpx2` itself, reaching even a
client the test never sees:
```
with MockedApis(things, widgets):
    ...
```
Either way a request no mock serves is refused unless `allow_network` lets it out.
`check_for_complaints` reports a call nothing served or a handler nothing called, and
`raise_for_complaints()` turns that report into a failure.
"""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Awaitable, Callable
from copy import deepcopy
from inspect import Parameter, isfunction, ismethod, signature
from types import MethodType
from typing import Any, get_type_hints, overload

import httpx2

from ghga_service_commons.httpyexpect.server.exceptions import HttpException

__all__ = [
    "NO_BODY",
    "PATH_CONVERTERS",
    "SUPPORTED_METHODS",
    "Endpoint",
    "HttpException",
    "MockSetupError",
    "MockedApi",
    "MockedApiTransport",
    "MockedApis",
    "NetworkPolicy",
    "NotMockedError",
    "ResponseHandler",
    "any_network",
    "endpoint",
    "fail_to_connect",
    "fail_with",
    "httpyexpect_body",
    "httpyexpect_response",
    "in_sequence",
    "local_network",
    "network_at",
    "no_network",
    "respond",
]


SUPPORTED_METHODS = ("GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE")
# What a path variable matches, keyed by the converter it names. Starlette's set, so a
# path lifted from the API being mocked means here what it means there.
PATH_CONVERTERS = {
    "str": "[^/]+",
    "int": "[0-9]+",
    "float": r"[0-9]+(?:\.[0-9]+)?",
    "uuid": "[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}",
    "path": ".*",
}
# A path variable, optionally naming one of the converters: `{name}` or `{name:path}`.
_PARAMETER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([a-zA-Z_][a-zA-Z0-9_]*))?\}")
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
VARIADIC_KINDS = (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD)
ResponseHandler = Callable[..., "httpx2.Response | Awaitable[httpx2.Response]"]
NetworkPolicy = Callable[[httpx2.URL], bool]


# Tells "no body at all" apart from a JSON `null`, which httpx2 cannot.
NO_BODY: Any = object()


class MockSetupError(AssertionError):
    """Raised when a mock is set up wrong to distinguish from actual test failures."""


class NotMockedError(MockSetupError):
    """Raised for a request no mock serves that the network policy does not let out."""


class _InSequence:
    """Answers consecutive requests with one handler each."""

    def __init__(self, handlers: tuple[ResponseHandler, ...]) -> None:
        self._remaining = list(handlers)

    def __call__(
        self, request: httpx2.Request, **path_variables: str
    ) -> httpx2.Response | Awaitable[httpx2.Response]:
        """Answer with the next handler in line, refusing once they are used up."""
        if not self._remaining:
            raise MockSetupError(f"Unexpected additional request to {request.url}")
        return self._remaining.pop(0)(request, **path_variables)


class Endpoint:
    """One endpoint of an API, declared in the class body of a `MockedApi`.

    `path` is relative to the base URL, and its `{variables}` reach the handler.
    """

    def __init__(
        self, method: str, path: str, default: ResponseHandler | None = None
    ) -> None:
        """Declare an endpoint served under `path`."""
        if method.upper() not in SUPPORTED_METHODS:
            raise MockSetupError(
                f"Endpoint {path!r} is declared under {method.upper()}, which is not an"
                f" HTTP method. Supported methods: {', '.join(SUPPORTED_METHODS)}."
            )
        if not path.startswith("/"):
            path = "/" + path

        self.method = method.upper()
        self.path = path
        self.pattern = _compiled(path)
        self.name = ""
        self.default: ResponseHandler = default or _unconfigured(self)
        self.is_method = False

    def __call__(self, handler: ResponseHandler) -> Endpoint:
        """Allows the endpoint to be used as decorator."""
        self.default = handler
        self.is_method = True
        return self

    def __set_name__(self, owner: type, name: str) -> None:
        """Take the attribute name the class body binds this endpoint to."""
        self.name = name

    # The overloads let a test read the handler, and `MockedApi` read the endpoint.
    @overload
    def __get__(self, obj: None, objtype: type | None = None) -> Endpoint: ...

    @overload
    def __get__(
        self, obj: MockedApi, objtype: type | None = None
    ) -> ResponseHandler: ...

    def __get__(
        self, obj: MockedApi | None, objtype: type | None = None
    ) -> Endpoint | ResponseHandler:
        """Get the handler this endpoint currently answers with."""
        return self if obj is None else obj._handlers[self.name]

    def __set__(self, obj: MockedApi, handler: ResponseHandler) -> None:
        """Set `handler` to answer with from now on.

        Records the call count it was set at, so `unused_handlers` can tell a handler
        the test set up from a default it never touched.
        """
        obj._handlers[self.name] = handler
        obj._configured_at[self.name] = len(obj.calls[self.name])


def local_network(url: httpx2.URL) -> bool:
    """Allow requests to loopback, `*.internal` and private addresses."""
    host = url.host
    if host in LOOPBACK_HOSTS or host.endswith(".internal"):
        return True
    try:
        return ipaddress.ip_address(host).is_private
    except ValueError:
        return False


def no_network(url: httpx2.URL) -> bool:
    """Let nothing out: every request has to be served by a mock."""
    return False


class MockedApi:
    """A mock of one HTTP API, answering the calls a service makes to it.

    Set `base_url`, and declare endpoints with `endpoint(...)`.
    """

    base_url: str

    def __init__(self, base_url: str = "") -> None:
        """Serve the API at `base_url`, or at the one the class declares."""
        base_url = base_url or getattr(type(self), "base_url", "")
        if not base_url:
            raise MockSetupError(
                f"{type(self).__name__} needs the base URL of the API it serves. Declare"
                " it as a `base_url` class attribute or pass it to the constructor."
            )
        self.base_url = _normalized(base_url)
        self._base = httpx2.URL(self.base_url)
        self._base_path = self._base.path.rstrip("/")
        self._endpoints = _declared_endpoints(type(self))

        self.requests: list[httpx2.Request] = []
        self.unmatched: list[httpx2.Request] = []
        self.calls: dict[str, list[httpx2.Request]] = {}
        self._handlers: dict[str, ResponseHandler] = {}
        self._configured_at: dict[str, int] = {}
        self.reset()

    def _answer(self, request: httpx2.Request, path: str) -> httpx2.Response:
        """Answer a request made by a synchronous client."""
        try:
            response = self._handle(request, path)
        except HttpException as error:
            return httpyexpect_response(error)
        if isinstance(response, Awaitable):
            _discard(response)
            raise MockSetupError(
                f"The handler answering {request.url} is async, but the call was made by"
                " a synchronous client. Use an async client, or a handler that is not"
                " async."
            )
        return response

    async def _answer_async(
        self, request: httpx2.Request, path: str
    ) -> httpx2.Response:
        """Answer a request made by an asynchronous client."""
        try:
            response = self._handle(request, path)
            return await response if isinstance(response, Awaitable) else response
        except HttpException as error:
            return httpyexpect_response(error)

    def _handle(
        self, request: httpx2.Request, path: str
    ) -> httpx2.Response | Awaitable[httpx2.Response]:
        """Record the request, then let the endpoint serving `path` answer it."""
        self.requests.append(request)
        matched = self._match(request.method, path)
        if matched is None:
            self.unmatched.append(request)
            raise NotMockedError(
                f"{type(self).__name__} was asked for {request.method} {request.url},"
                " which none of its endpoints serve."
            )
        declared, path_variables = matched
        self.calls[declared.name].append(request)
        handler = self._handlers[declared.name]
        return handler(
            request, **_bind_and_cast_path_vars(handler, path_variables, request)
        )

    def _match(self, method: str, path: str) -> tuple[Endpoint, dict[str, str]] | None:
        """Find the endpoint serving `method` and `path` and its path variables."""
        for declared in self._endpoints.values():
            if declared.method != method:
                continue
            matched = declared.pattern.fullmatch(path)
            if matched:
                return declared, matched.groupdict()
        return None

    def _path_relative_to_base_url(self, url: httpx2.URL) -> str | None:
        """The path `url` addresses within this API, or None if it lies outside it."""
        base = self._base
        if (url.scheme, url.host, url.port) != (
            base.scheme,
            base.host,
            base.port,
        ) or not url.path.startswith(self._base_path):
            return None

        path = url.path[len(self._base_path) :]
        if not path:
            return "/"
        return path if path.startswith("/") else None

    def reset(self) -> None:
        """Forget every recorded request and put the default handlers back."""
        self.requests.clear()
        self.unmatched.clear()
        self.calls = {name: [] for name in self._endpoints}
        self._configured_at = {}
        self._handlers = {
            name: self._default_handler(declared)
            for name, declared in self._endpoints.items()
        }

    def _default_handler(self, declared: Endpoint) -> ResponseHandler:
        """Get the handler an endpoint starts out answering with.

        A method - the decorator form - is bound to this mock. Anything else is copied,
        so a stateful default is not shared between mocks.
        """
        if declared.is_method:
            return MethodType(declared.default, self)
        return deepcopy(declared.default)

    @property
    def last_request(self) -> httpx2.Request | None:
        """The most recent request that reached this mock."""
        if not self.requests:
            return None
        return self.requests[-1]

    @property
    def unused_handlers(self) -> list[str]:
        """The endpoints that were set up, but never called."""
        return [
            name
            for name, configured_at in self._configured_at.items()
            if len(self.calls[name]) <= configured_at
        ]

    def as_transport(
        self, allow_network: NetworkPolicy = no_network
    ) -> MockedApiTransport:
        """Get a transport serving this mock alone.

        `MockedApis(...).as_transport()` is the way to serve several at once, or to
        pass an `inner` transport for what `allow_network` lets out.
        """
        return MockedApis(self, allow_network=allow_network).as_transport()


class MockedApis:
    """Wraps a collection of `MockedApi`s and deals with routing requests to the correct one."""

    def __init__(
        self, *apis: MockedApi, allow_network: NetworkPolicy = local_network
    ) -> None:
        self.apis = list(apis)
        self.allow_network = allow_network
        self._replaced: tuple[Callable, Callable] | None = None
        self._installed: tuple[Callable, Callable] | None = None

        claimed: dict[str, MockedApi] = {}
        for api in self.apis:
            if api.base_url in claimed:
                raise MockSetupError(
                    f"{type(api).__name__} and {type(claimed[api.base_url]).__name__}"
                    f" both serve {api.base_url}, so only one of them would ever answer."
                    " Declare the endpoints on one mock instead."
                )
            claimed[api.base_url] = api

        # longest base URL first, so an API nested under another one gets its own calls
        self._routes = sorted(
            self.apis, key=lambda api: len(api.base_url), reverse=True
        )

    def __enter__(self) -> MockedApis:
        """Install the mocks when used as context manager."""
        self.install()
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Take the mocks off, leaving `verify` to whoever wants to look."""
        self.uninstall()

    def _route(self, request: httpx2.Request) -> tuple[MockedApi, str] | None:
        """Route to the correct API.

        Raise if this would route to a non-mocked endpoint disallowed by `allow_network`.
        Return None if the request doesn't hit a MockedAPI and is allowed to hit the real network.
        """
        url = _canonical_loopback(request.url)
        for api in self._routes:
            path = api._path_relative_to_base_url(url)
            if path is not None:
                return api, path
        if not self.allow_network(url):
            raise NotMockedError(
                f"A test tried to reach {request.url}, which is neither one of the"
                " mocked APIs nor a real endpoint permitted by `allow_network`."
            )
        return None

    def _answered(
        self, request: httpx2.Request, unmocked: Callable[[], httpx2.Response]
    ) -> httpx2.Response:
        """Let the mock serving the request answer it, else fall through to `unmocked`."""
        route = self._route(request)
        if route is None:
            return unmocked()
        api, path = route
        return api._answer(request, path)

    async def _answered_async(
        self,
        request: httpx2.Request,
        unmocked: Callable[[], Awaitable[httpx2.Response]],
    ) -> httpx2.Response:
        """Answer an asynchronous caller the way `_answered` answers a synchronous one."""
        route = self._route(request)
        if route is None:
            return await unmocked()
        api, path = route
        return await api._answer_async(request, path)

    def as_transport(self, inner: Any = None) -> MockedApiTransport:
        """Return a transport serving these mocks, for a Client or an AsyncClient.

        Use it where the code under test takes a transport, so only the clients built
        with it are mocked. `install()` is for the code that gives no such opening.

        A request no mock serves and `allow_network` permits goes to `inner`, which also
        makes this stackable as the innermost layer of a transport stack.
        """
        return MockedApiTransport(self, inner)

    def install(self) -> None:
        """Intercept every `httpx2` call until `uninstall` is called."""
        if self._installed:
            raise MockSetupError(
                "These mocks are already installed. Installing them again would lose"
                " what they replaced, leaving it patched after the test."
            )

        network = httpx2.HTTPTransport.handle_request
        network_async = httpx2.AsyncHTTPTransport.handle_async_request

        def handle_request(
            transport: httpx2.HTTPTransport, request: httpx2.Request
        ) -> httpx2.Response:
            """Answer a request made by a synchronous client."""
            return self._answered(request, lambda: network(transport, request))

        async def handle_async_request(
            transport: httpx2.AsyncHTTPTransport, request: httpx2.Request
        ) -> httpx2.Response:
            """Answer a request made by an asynchronous client."""
            return await self._answered_async(
                request, lambda: network_async(transport, request)
            )

        self._replaced = (network, network_async)
        self._installed = (handle_request, handle_async_request)
        httpx2.HTTPTransport.handle_request = handle_request  # type: ignore[assignment,method-assign]
        httpx2.AsyncHTTPTransport.handle_async_request = handle_async_request  # type: ignore[assignment,method-assign]

    def uninstall(self) -> None:
        """Reset mocked methods to their previous state."""
        if self._installed is None or self._replaced is None:
            return
        installed_now = (
            httpx2.HTTPTransport.handle_request,
            httpx2.AsyncHTTPTransport.handle_async_request,
        )
        if installed_now != self._installed:
            raise MockSetupError(
                "These mocks were installed before another set that is still installed,"
                " so they cannot be taken off yet. Uninstall the sets in the order they"
                " were installed."
            )
        network, network_async = self._replaced
        httpx2.HTTPTransport.handle_request = network  # type: ignore[method-assign]
        httpx2.AsyncHTTPTransport.handle_async_request = network_async  # type: ignore[method-assign]
        self._replaced = None
        self._installed = None

    def check_for_complaints(self) -> list[str]:
        """Report anything the test set up wrong.

        Both directions: a call that reached a mock with no endpoint for it, and an
        endpoint a test configured that nothing ever asked for.
        """
        complaints: list[str] = []
        for api in self.apis:
            name = type(api).__name__
            for request in api.unmatched:
                complaints.append(
                    f"{name} was asked for {request.method} {request.url}, which none of"
                    " its endpoints serve."
                )
            for unused in api.unused_handlers:
                complaints.append(
                    f"{name}.{unused} was given a handler that nothing called."
                )
        return complaints

    def raise_for_complaints(self) -> None:
        """Raise whatever `check_for_complaints` found."""
        complaints = self.check_for_complaints()
        if complaints:
            raise MockSetupError("\n".join(complaints))

    def reset(self) -> None:
        """Reset all MockAPIs."""
        for api in self.apis:
            api.reset()


class MockedApiTransport(httpx2.BaseTransport, httpx2.AsyncBaseTransport):
    """Serves a set of mocks to the clients it is mounted on.

    Answers both kinds of caller, so a fixture handing one out can say it returns this
    rather than having to narrow to the sync or the async half.
    """

    def __init__(self, mocks: MockedApis, inner: Any = None) -> None:
        """Answer from `mocks`, passing anything they do not serve to `inner`."""
        self._mocks = mocks
        self._inner = inner

    def _refuse(self, request: httpx2.Request) -> httpx2.Response:
        """Explain that a permitted request has nowhere to go from here."""
        raise MockSetupError(
            f"{request.url} is not served by any of these mocks, and `allow_network`"
            " lets it out - but this transport has nothing to send it with. Pass the"
            " transport to send it with as `as_transport(inner=...)`, or tighten"
            " `allow_network` so the call is refused where it is made."
        )

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        """Answer a request made by a synchronous client."""
        return self._mocks._answered(
            request,
            lambda: (
                self._inner.handle_request(request)
                if self._inner is not None
                else self._refuse(request)
            ),
        )

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Answer a request made by an asynchronous client."""
        await request.aread()

        async def unmocked() -> httpx2.Response:
            """Send the request on, if there is anything to send it with."""
            if self._inner is None:
                return self._refuse(request)
            return await self._inner.handle_async_request(request)

        return await self._mocks._answered_async(request, unmocked)

    def close(self) -> None:
        """Close the transport underneath, which this one was handed to close."""
        if self._inner is not None:
            self._inner.close()

    async def aclose(self) -> None:
        """Close the transport underneath, the way an asynchronous client asks."""
        if self._inner is not None:
            await self._inner.aclose()


def _compiled(path: str) -> re.Pattern[str]:
    """Turn a path into a pattern matching it, capturing its `{variable}` placeholders.

    Anything brace-shaped that is not a variable - `{item-id}`, which FastAPI does not
    read as one either - is matched literally.
    """
    pattern = ""
    end = 0
    seen: set[str] = set()
    for variable in _PARAMETER.finditer(path):
        name, converter = variable.group(1), variable.group(2) or "str"
        if converter not in PATH_CONVERTERS:
            raise MockSetupError(
                f"Path {path!r} matches {name!r} with {converter!r}, which is not a path"
                f" converter. Supported converters: {', '.join(PATH_CONVERTERS)}."
            )
        if name in seen:
            raise MockSetupError(
                f"Path {path!r} declares {name!r} more than once, so the handler cannot"
                " be told which of them a request meant. Give each variable its own name."
            )
        seen.add(name)
        pattern += re.escape(path[end : variable.start()])
        pattern += f"(?P<{name}>{PATH_CONVERTERS[converter]})"
        end = variable.end()
    return re.compile(pattern + re.escape(path[end:]))


def _bind_and_cast_path_vars(
    handler: ResponseHandler, path_variables: dict[str, str], request: httpx2.Request
) -> dict[str, Any]:
    """Cast the path variables to the types `handler` declares for them.

    Two failures, two audiences: a variable the handler cannot take is a `MockSetupError`
    because the test wired up the wrong handler; a value that will not cast is a 422
    because that is what the real API would answer.
    """
    named, collects_the_rest = _wanted(handler)

    bound_path_variables: dict[str, Any] = {}
    for name, value in path_variables.items():
        if name not in named:
            if not collects_the_rest:
                raise MockSetupError(
                    f"The handler answering {request.url} takes no {name!r}, which the"
                    f" endpoint's path declares. Give it a {name!r} parameter, or a"
                    " `**path_variables` one to collect what it does not name."
                )
            bound_path_variables[name] = value
            continue

        wanted_type = named[name]
        if wanted_type is str:
            bound_path_variables[name] = value
            continue
        try:
            bound_path_variables[name] = wanted_type(value)
        except (ValueError, TypeError) as error:
            raise HttpException(
                status_code=422,
                exception_id="malformedUrl",
                description=(
                    f"Unable to cast '{value}' to {wanted_type} for"
                    f" path '{request.url.path}'"
                ),
                data={
                    "value": value,
                    "parameter_type": str(wanted_type),
                    "path": request.url.path,
                },
            ) from error

    return bound_path_variables


def _wanted(handler: ResponseHandler) -> tuple[dict[str, Any], bool]:
    """Returns the path variables `handler` names with their types, and whether it takes the rest.

    An unannotated parameter stays the string the URL carried. `request` is passed
    positionally, so it is not one of the variables to bind.
    """
    parameters = signature(handler).parameters
    is_plain = isfunction(handler) or ismethod(handler)
    annotated = handler if is_plain else type(handler).__call__
    try:
        hints = get_type_hints(annotated)
    # annotations that will not resolve leave every variable binding as a string
    except Exception:
        hints = {}

    named = {
        name: hints.get(name, str)
        for name, parameter in parameters.items()
        if name != "request" and parameter.kind not in VARIADIC_KINDS
    }
    collects_the_rest = any(
        parameter.kind is Parameter.VAR_KEYWORD for parameter in parameters.values()
    )
    return named, collects_the_rest


def _unconfigured(declared: Endpoint) -> ResponseHandler:
    """Build a handler for an endpoint no test has said how to answer."""

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Refuse to make up a response."""
        raise MockSetupError(
            f"Unexpected request to {request.url}. Assign a handler to"
            f" `{declared.name}` if the test is meant to call this endpoint."
        )

    return handler


def _normalized(base_url: str) -> str:
    """Spell a base URL the one way everything downstream compares against."""
    url = _canonical_loopback(httpx2.URL(base_url)).copy_with(query=None, fragment=None)
    if not url.scheme or not url.host:
        raise MockSetupError(f"Base URL {base_url!r} needs a scheme and a host")
    return str(url).rstrip("/")


def _canonical_loopback(url: httpx2.URL) -> httpx2.URL:
    """Rewrite the loopback aliases to one spelling, leaving any other host alone."""
    return url.copy_with(host="127.0.0.1") if url.host in LOOPBACK_HOSTS else url


def _declared_endpoints(mock_class: type) -> dict[str, Endpoint]:
    """Collect the endpoints a mock class declares, a subclass overriding its bases."""
    endpoints: dict[str, Endpoint] = {}
    for base in reversed(mock_class.__mro__):
        for name, attribute in vars(base).items():
            if isinstance(attribute, Endpoint):
                endpoints[name] = attribute
    return endpoints


def _discard(response: Awaitable) -> None:
    """Close a coroutine nothing will await, so Python does not warn about it later."""
    close = getattr(response, "close", None)
    if close is not None:
        close()


def httpyexpect_response(error: HttpException) -> httpx2.Response:
    """Turn a httpyexpect exception into the response a real API would send."""
    body = httpyexpect_body(
        error.body.exception_id, error.body.description, error.body.data
    )
    return httpx2.Response(error.status_code, json=body)


def httpyexpect_body(
    exception_id: str, description: str = "", data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the body of a httpyexpect error response."""
    return {
        "exception_id": exception_id,
        "description": description,
        "data": data or {},
    }


def any_network(url: httpx2.URL) -> bool:
    """Let out everything no mock serves, including calls to the internet."""
    return True


def endpoint(
    method: str, path: str, default: ResponseHandler | None = None
) -> Endpoint:
    """Declare an endpoint of a `MockedApi`. See `Endpoint`."""
    return Endpoint(method, path, default)


def fail_to_connect(reason: str = "All connection attempts failed") -> ResponseHandler:
    """Build a handler that makes the API look unreachable."""

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Refuse the connection."""
        raise httpx2.ConnectError(reason, request=request)

    return handler


def fail_with(error: Exception) -> ResponseHandler:
    """Build a handler that raises `error` instead of answering."""

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Raise instead of answering."""
        raise error

    return handler


def in_sequence(*handlers: ResponseHandler) -> ResponseHandler:
    """Build a handler answering consecutive requests with `handlers`, then failing."""
    return _InSequence(handlers)


def network_at(*hosts: str) -> NetworkPolicy:
    """Let out only the calls to the named hosts."""
    allowed = frozenset(hosts)

    def policy(url: httpx2.URL) -> bool:
        """Whether the request is bound for one of the named hosts."""
        return url.host in allowed

    return policy


def respond(
    status_code: int = 200,
    *,
    json: Any = NO_BODY,
    content: bytes | str | None = None,
    headers: dict[str, str] | None = None,
) -> ResponseHandler:
    """Build a handler that always answers the same way.

    `json=None` is a JSON `null`; without `json` the body is `content`, or nothing.
    """

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Answer with the stored response."""
        if json is NO_BODY:
            return httpx2.Response(status_code, content=content, headers=headers)
        if json is None:
            # httpx2 would read `json=None` as no body, so encode `null` by hand
            return httpx2.Response(
                status_code,
                content=b"null",
                headers={"content-type": "application/json", **(headers or {})},
            )
        return httpx2.Response(status_code, json=json, headers=headers)

    return handler
