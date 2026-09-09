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
class MockedEkssApi(MockedApi):
    base_url = "http://ekss.test/api"

    @endpoint("GET", "/secrets/{secret_id}")
    def on_get_secret(request, *, secret_id: UUID) -> httpx2.Response:
        ...
```
Give the handler `self` as its first parameter and it is bound to the mock instead, so
it can answer out of state the test sets on the mock rather than by being swapped out:
```
    @endpoint("GET", "/secrets/{secret_id}")
    def on_get_secret(self, request, *, secret_id: UUID) -> httpx2.Response:
        return httpx2.Response(200, json=self.secrets[secret_id])
```
A `{variable}` in the path reaches the handler as the parameter of that name, cast to
the type it is annotated with, or lands in a `**path_variables` parameter if the handler
declares one.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from copy import deepcopy
from inspect import Parameter, isfunction, ismethod, signature
from typing import Any, get_type_hints, overload

import httpx2

from ghga_service_commons.httpyexpect.server.exceptions import HttpException

__all__ = [
    "SUPPORTED_METHODS",
    "Endpoint",
    "HttpException",
    "MockSetupError",
    "MockedApi",
    "NotMockedError",
    "ResponseHandler",
    "endpoint",
    "httpyexpect_body",
    "httpyexpect_response",
]


SUPPORTED_METHODS = ("GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE")
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
VARIADIC_KINDS = (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD)

ResponseHandler = Callable[..., "httpx2.Response | Awaitable[httpx2.Response]"]


class MockSetupError(AssertionError):
    """Raised when a mock is set up wrong to distinguish from actual test failures."""


class NotMockedError(MockSetupError):
    """Raised when a test is about to send a request to an (unmocked) endpoint that's not allowed by network policy."""


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

    def __call__(self, handler: ResponseHandler) -> Endpoint:
        """Take the decorated function as the handler to answer with by default.

        Lets an endpoint be declared over a function body rather than beside one:
        ```
        @endpoint("GET", "/secrets/{secret_id}")
        def on_get_secret(request, *, secret_id: str) -> httpx2.Response: ...
        ```
        """
        self.default = handler
        return self

    def __set_name__(self, owner: type, name: str) -> None:
        """Set endpoint name."""
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
        """Set `handler` to answer with from now on."""
        obj._handlers[self.name] = handler
        obj._configured_at[self.name] = len(obj.calls[self.name])


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
                " it as a `base_url` class attribute, or pass it to the constructor."
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
        return handler(request, **_bound(handler, path_variables, request))

    def _match(self, method: str, path: str) -> tuple[Endpoint, dict[str, str]] | None:
        """Find the endpoint serving `method` and `path`, with its path variables."""
        for declared in self._endpoints.values():
            if declared.method != method:
                continue
            matched = declared.pattern.fullmatch(path)
            if matched:
                return declared, matched.groupdict()
        return None

    def _path_of(self, url: httpx2.URL) -> str | None:
        """The path `url` addresses within this API, or None if it lies outside it."""
        base = self._base
        if (url.scheme, url.host, url.port) != (base.scheme, base.host, base.port):
            return None
        if not url.path.startswith(self._base_path):
            return None
        path = url.path[len(self._base_path) :]
        if not path:
            return "/"
        return path if path.startswith("/") else None

    def reset(self) -> None:
        """Reset the API state."""
        self.requests.clear()
        self.unmatched.clear()
        self.calls = {name: [] for name in self._endpoints}
        self._configured_at = {}
        self._handlers = {
            name: self._default_handler(declared.default)
            for name, declared in self._endpoints.items()
        }

    def _default_handler(self, default: ResponseHandler) -> ResponseHandler:
        """Get the handler an endpoint starts out answering with.

        A default written as a method - its first parameter named `self` - is bound to
        this mock, so it can answer out of state the test sets on the mock rather than
        by being swapped out. Anything else is copied, so a stateful default like
        `in_sequence` starts over for every mock rather than being used up once.
        """
        if isfunction(default):
            first = next(iter(signature(default).parameters), None)
            if first == "self":
                return default.__get__(self)
        return deepcopy(default)

    @property
    def last_request(self) -> httpx2.Request:
        """The most recent request that reached this mock."""
        if not self.requests:
            raise AssertionError(f"No request reached the {type(self).__name__}")
        return self.requests[-1]

    @property
    def unused_handlers(self) -> list[str]:
        """The endpoints that were set up, but never called."""
        return [
            name
            for name, configured_at in self._configured_at.items()
            if len(self.calls[name]) <= configured_at
        ]


def _compiled(path: str) -> re.Pattern[str]:
    """Turn a path into a pattern matching it, capturing its `{variable}` placeholders."""
    parts = re.split(r"\{([^{}]*)\}", path)
    return re.compile(
        "".join(
            re.escape(part) if index % 2 == 0 else f"(?P<{part}>[^/]+)"
            for index, part in enumerate(parts)
        )
    )


def _wanted(handler: ResponseHandler) -> tuple[dict[str, Any], bool]:
    """The path variables `handler` names with their types, and whether it takes the rest.

    A parameter with no annotation is left as the string the URL carried. `request` is
    passed positionally, so it is not one of the variables to bind.
    """
    parameters = signature(handler).parameters
    is_plain = isfunction(handler) or ismethod(handler)
    annotated = handler if is_plain else type(handler).__call__
    try:
        hints = get_type_hints(annotated)
    except Exception:  # a handler whose annotations cannot be resolved binds as strings
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


def _bound(
    handler: ResponseHandler, path_variables: dict[str, str], request: httpx2.Request
) -> dict[str, Any]:
    """Cast the path variables to the types `handler` declares for them.

    A variable the handler does not name stays a string and goes to its `**kwargs`, or
    is a `MockSetupError` if it has none - that is the test wiring up a handler that
    cannot serve the endpoint. A value that will not cast is an `HttpException` with
    status 422 instead, because that is the API answering a URL it cannot read.
    """
    named, collects_the_rest = _wanted(handler)

    bound: dict[str, Any] = {}
    for name, value in path_variables.items():
        if name not in named:
            if not collects_the_rest:
                raise MockSetupError(
                    f"The handler answering {request.url} takes no {name!r}, which the"
                    f" endpoint's path declares. Give it a {name!r} parameter, or a"
                    " `**path_variables` one to collect what it does not name."
                )
            bound[name] = value
            continue

        wanted_type = named[name]
        if wanted_type is str:
            bound[name] = value
            continue
        try:
            bound[name] = wanted_type(value)
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

    return bound


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
    """Close a coroutine nothing is going to await, so it does not resurface later."""
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


def endpoint(
    method: str, path: str, default: ResponseHandler | None = None
) -> Endpoint:
    """Declare an endpoint of a `MockedApi`. See `Endpoint`."""
    return Endpoint(method, path, default)
