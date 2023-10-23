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
"""A class for mocking API endpoints when testing with the httpx_mock fixture."""

import re
from functools import partial
from inspect import signature
from typing import Any, Callable, Generic, Optional, TypeVar, cast, get_type_hints

import httpx
import pytest
from pydantic import BaseModel

from ghga_service_commons.httpyexpect.server.exceptions import HttpException

__all__ = [
    "MockRouter",
    "assert_all_responses_were_requested",
    "HttpException",
]

BRACKET_PATTERN = re.compile(r"{.*?}")


def _compile_regex_url(path: str) -> str:
    """Given a path, compile a url pattern regex that matches named groups where specified.

    e.g. "/work-packages/{package_id}" would become "/work-packages/(?P<package_id>[^/]+)$"
    And when a request URL like /work-packages/12 is matched against the regex-url above,
    the match object will have a .groupdict() of {"package_id": "12"}

    This function is not intended to be used outside the module.
    """
    brackets_to_strip = "{}"

    url = re.sub(
        BRACKET_PATTERN,
        repl=lambda name: f"(?P<{name.group().strip(brackets_to_strip)}>[^/]+)",
        string=path,
    )
    return f"{url}$"


def _get_signature_info(endpoint_function: Callable) -> dict[str, Any]:
    """Retrieve the typed parameter info from function signature minus return type.

    This function is not intended to be used outside the module.
    """
    signature_parameters: dict[str, Any] = get_type_hints(endpoint_function)
    if "return" in signature_parameters:
        signature_parameters.pop("return")
    return signature_parameters


@pytest.fixture
def assert_all_responses_were_requested() -> bool:
    """Whether httpx checks that all registered responses are sent back.

    This is set to false because the registered endpoints are considered mocked even if
    they aren't used in a given test. If this is True (default), pytest_httpx will raise
    an error if a given test doesn't hit every mocked endpoint.
    """
    return False


class RegisteredEndpoint(BaseModel):
    """Endpoint data with the url turned into regex string to get parameters in path."""

    url_pattern: str
    endpoint_function: Callable
    signature_parameters: dict[str, Any]


ExpectedExceptionTypes = TypeVar("ExpectedExceptionTypes", bound=Exception)


class MockRouter(Generic[ExpectedExceptionTypes]):
    """
    A class used to register mock endpoints with decorators similar to FastAPI.

    Tag endpoint functions with EndpointHandler.[method]("/some/url-with/{variables}").
    The regex compiler function will turn the url specified in the decorator function
    into a regex string capable of capturing the variables in the url (curly brackets)
    with named groups. That in turn enables linking the named path variables to the
    variables in the endpoint function itself.

    The only parameter types allowed in the endpoint functions are primitives
    that can be stored in the url string: int, float, str, bool, None, and complex.
    The one exception is "request", which will be passed in automatically if specified.
    """

    def __init__(
        self,
        exception_handler: Optional[
            Callable[[httpx.Request, ExpectedExceptionTypes], Any]
        ] = None,
        exceptions_to_handle: Optional[tuple[type[Exception], ...]] = None,
        handle_exception_subclasses: bool = False,
    ):
        """Initialize the MockRouter with an optional exception handler.

        Args:
            `exception_handler`:
                custom exception handler function that takes the request and exception
                as arguments, in that order. It must take an httpx.Request object as
                the first argument and any subclass of Exception as the second argument.
                This allows your exception handler signature to be more specifically typed.

            `exceptions_to_handle`:
                tuple containing the exception types to pass to the exception_handler.
                This parameter has no effect if `exception_handler` is None.
                If None, no exceptions will be passed to the handler. If provided, only
                the exceptions specified will be passed to the handler. All other exception
                types will be re-raised.

            `handle_exception_subclasses`:
                if True, will not only pass the specified exception types to the handler
                also any exceptions that subclass those types. When False, only exact
                matches will be passed to the handler.
        """
        self.exception_handler = exception_handler
        self.exceptions_to_handle = exceptions_to_handle
        self.handle_exception_subclasses = handle_exception_subclasses

        self._methods: dict[str, list[RegisteredEndpoint]] = {
            "GET": [],
            "DELETE": [],
            "POST": [],
            "PATCH": [],
            "PUT": [],
        }

    @staticmethod
    def _ensure_all_parameters_are_typed(
        endpoint_function: Callable, signature_parameters: dict[str, Any]
    ):
        """Verify that all the endpoint function parameters are typed.

        This will not apply to the request parameter because we don't perform any
        type conversion on that.

        Args:
            endpoint_function: the function associated with the endpoint.
            signature_parameters:
                A dict containing type information for the endpoint function's parameters.

        Raises:
            TypeError: When one or more parameters are missing type-hint information.
        """
        all_parameters = signature(endpoint_function).parameters

        for parameter in all_parameters:
            if parameter not in signature_parameters:
                raise TypeError(
                    f"Parameter '{parameter}' in '{endpoint_function.__name__}' is "
                    + "missing a type hint"
                )

    @staticmethod
    def _ensure_decorator_and_endpoint_parameters_match(
        path: str, signature_parameters: dict[str, Any]
    ):
        """Verify consistency between path in path decorator and the decorated function.

        Args:
            path: the path specified by the MockRouter decorator.
            signature_parameters:
                A dict containing type information for the endpoint function's parameters.

        Raises:
            TypeError: When there is a mismatch between the path and the function parameters.
        """
        endpoint_parameters = {
            param for param in signature_parameters if param != "request"
        }
        if endpoint_parameters:
            # get set of parameters from path with brackets stripped
            matches = {param.strip("{}") for param in re.findall(BRACKET_PATTERN, path)}

            if matches != endpoint_parameters:
                raise TypeError(
                    f"Path variables for path '{path}' do not match the "
                    + "function it decorates"
                )

    def _add_endpoint(
        self, method: str, path: str, endpoint_function: Callable
    ) -> None:
        """Register an endpoint.

        Process the `path` and store the resulting endpoint according to `method`.
        """
        signature_parameters: dict[str, Any] = _get_signature_info(endpoint_function)

        url_pattern = _compile_regex_url(path)

        registered_endpoint = RegisteredEndpoint(
            url_pattern=url_pattern,
            endpoint_function=endpoint_function,
            signature_parameters=signature_parameters,
        )

        self._methods[method].append(registered_endpoint)

    def _validate_endpoint(self, path: str, endpoint_function: Callable):
        """Perform validation on the endpoint before adding it.

        Verify that all the `endpoint_function` parameters are typed.
        Verify that the `path` parameter names match the `endpoint_function` signature.
        """
        signature_parameters: dict[str, Any] = _get_signature_info(endpoint_function)
        self._ensure_all_parameters_are_typed(endpoint_function, signature_parameters)
        self._ensure_decorator_and_endpoint_parameters_match(path, signature_parameters)

    def _base_endpoint_wrapper(
        self, path: str, method: str, endpoint_function: Callable
    ) -> Callable:
        """Logic common to endpoint decorators to validate/register the target function.

        This is just moved out to avoid typing it in each of `get`, `delete`, `post`, etc.
        """
        self._validate_endpoint(path, endpoint_function)
        self._add_endpoint(
            method=method, path=path, endpoint_function=endpoint_function
        )
        return endpoint_function

    def get(self, path: str) -> Callable:
        """Add endpoint to Handler with `GET` method."""
        return partial(self._base_endpoint_wrapper, path, "GET")

    def delete(self, path: str) -> Callable:
        """Add endpoint to Handler with `DELETE` method."""
        return partial(self._base_endpoint_wrapper, path, "DELETE")

    def post(self, path: str) -> Callable:
        """Add endpoint to Handler with `POST` method."""
        return partial(self._base_endpoint_wrapper, path, "POST")

    def patch(self, path: str) -> Callable:
        """Add endpoint to Handler with `PATCH` method."""
        return partial(self._base_endpoint_wrapper, path, "PATCH")

    def put(self, path: str) -> Callable:
        """Add endpoint to Handler with `PUT` method."""
        return partial(self._base_endpoint_wrapper, path, "PUT")

    @staticmethod
    def _convert_parameter_types(
        parsed_url_parameters: dict[str, str],
        signature_parameters: dict[str, Any],
        request: httpx.Request,
    ) -> dict[str, Any]:
        """Get type info for function parameters.

        Since the values parsed from the URL are still in string format, cast them to
        the types specified in the signature.
        If the request is needed, include that in the returned parameters.

        Args:
            parsed_url_parameters:
                A dict containing the path variable names (keys) as specified in the
                function decorator, and the values supplied for those variables in the
                request still in string format (values).
            signature_parameters:
                A dict containing type information for the endpoint function's parameters.
            request:
                The request object.

        Raises:
            HttpException:
                (with status 422) when a string value in the request URL cannot
                be converted/cast to the type specified by the type-hint for the
                corresponding parameter.
        """
        # type-cast based on type-hinting info
        typed_parameters: dict[str, Any] = {}
        for parameter_name, value in parsed_url_parameters.items():
            parameter_type = signature_parameters[parameter_name]

            if parameter_type is not str:
                try:
                    value = parameter_type(value)
                except ValueError as err:
                    raise HttpException(
                        status_code=422,
                        exception_id="malformedUrl",
                        description=(
                            f"Unable to cast '{value}' to {parameter_type} for "
                            + f"path '{request.url.path}'"
                        ),
                        data={
                            "value": value,
                            "parameter_type": parameter_type,
                            "path": request.url.path,
                        },
                    ) from err
            typed_parameters[parameter_name] = value

        # include request itself if needed (e.g. for header or auth info),
        if "request" in signature_parameters:
            typed_parameters["request"] = request

        return typed_parameters

    def _parse_url_parameters(
        self, url: str, endpoint: RegisteredEndpoint
    ) -> dict[str, str]:
        """Produce a dict of path var names (keys) and request url values (values).

        This should always match because we will have already performed the match in
        _get_registered_endpoint.
        """
        matched_url = re.search(endpoint.url_pattern, url)
        matched_url = cast(re.Match, matched_url)  # never None, make type checker happy
        return matched_url.groupdict()

    def _get_registered_endpoint(self, url: str, method: str) -> RegisteredEndpoint:
        """Match request URL to a registered endpoint's url pattern.

        Iterate through the registered endpoints for the given method.
        For each registered endpoint, try to match the request's url to the endpoint
        pattern. Upon matching, return the endpoint object.

        Args:
            url: The url of the request.
            method: The method of the request.

        Raises:
            HttpException:
                (with status 404) when unable to find a registered endpoint with a
                matching URL.
        """
        for endpoint in self._methods[method]:
            matched_url = re.search(endpoint.url_pattern, url)
            if matched_url:
                return endpoint

        raise HttpException(
            status_code=404,
            exception_id="pageNotFound",
            description=f"No registered path found for url '{url}' and method '{method}'",
            data={"url": url, "method": method},
        )

    def _build_loaded_endpoint_function(self, request: httpx.Request) -> partial:
        """Match a request to the correct endpoint.

        Based on the endpoint matched, build the typed parameter dictionary and
        return the loaded partial function.
        """
        url = str(request.url)

        # get endpoint object that corresponds to the request URL
        endpoint = self._get_registered_endpoint(url=url, method=request.method)

        # get the parsed string parameters from the url
        parsed_url_parameters = self._parse_url_parameters(url=url, endpoint=endpoint)

        # convert parsed string parameters into the types specified in function signature
        typed_parameters = self._convert_parameter_types(
            parsed_url_parameters=parsed_url_parameters,
            signature_parameters=endpoint.signature_parameters,
            request=request,
        )

        # return function with the typed parameters loaded up
        return partial(endpoint.endpoint_function, **typed_parameters)

    def _should_pass_to_handler(self, exc: Exception):
        """Determine whether the provided exception should be passed to the handler."""
        if not self.exceptions_to_handle:
            return False

        pass_to_handler = False
        for exc_type in self.exceptions_to_handle:
            if isinstance(exc, exc_type) and (
                self.handle_exception_subclasses
                or (not self.handle_exception_subclasses and type(exc) is exc_type)
            ):
                pass_to_handler = True
        return pass_to_handler

    def handle_request(self, request: httpx.Request):
        """Route intercepted request to the registered endpoint and return response.

        If using this with httpx_mock, then this function should be the callback.
        e.g.:
        ```
        httpx_mock.add_callback(callback=mock_router.handle_request)
        ```
        If self.exception_handler is specified, any errors matching self.exceptions_to_handle
        will be passed to the handler. In all other cases, the exception will be
        re-raised.
        """
        try:
            endpoint_function = self._build_loaded_endpoint_function(request)
            return endpoint_function()
        except Exception as exc:
            if self.exception_handler and self._should_pass_to_handler(exc):
                exc = cast(
                    ExpectedExceptionTypes, exc
                )  # satisfy type-checker by making exc type 'E'
                return self.exception_handler(request, exc)
            raise
