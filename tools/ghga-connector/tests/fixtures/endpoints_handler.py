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

"""A class to register mock endpoint functions in a similar fashion to FastAPI with
class methods that can process an incoming request with a dynamic url pattern"""

import logging
import re
from functools import partial
from typing import Any, Callable, get_type_hints

import httpx
from pydantic import BaseModel

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class MatchableEndpoint(BaseModel):
    """Endpoint data with the url turned into regex string to get parameters in path"""

    url_pattern: str
    endpoint_function: Callable


class EndpointsHandler:
    """
    A class used to register mock endpoints with decorators similar to FastAPI.
    Tag endpoint functions with EndpointHandler.get("/some/url-with/{variables}").
    .post and .patch are also implemented at the moment.
    The regex compiler function will turn the url specified in the decorator function
    into a regex string capable of capturing the variables in the url (curly brackets)
    with named groups. That in turn enables linking the named path variables to the
    variables in the endpoint function itself.
    """

    _methods: dict[str, list[MatchableEndpoint]] = {
        "GET": [],
        "POST": [],
        "PATCH": [],
    }

    @staticmethod
    def _compile_regex_url(url_pattern: str):
        """Given a url pattern, compile a regex that matches named groups where specified
        e.g. "/work-packages/{package_id}" would become "/work-packages/(?P<package_id>[^\/]+)"
        And when a request URL like /work-packages/12 is matched against the regex-url above,
        the match object will have a .groupdict() of {"package_id": "12"}
        """

        strip = "{}"
        parameter_pattern = re.compile(r"{.*?}")  # match fewest possible chars inside

        url = re.sub(
            parameter_pattern,
            repl=lambda name: f"(?P<{name.group().strip(strip)}>[^/]+)",
            string=url_pattern,
        )
        return url

    @classmethod
    def _add_endpoint(cls, method: str, url: str, endpoint_function: Callable):
        """Process url and store endpoint according to method type"""
        url_pattern = cls._compile_regex_url(url)
        matchable_endpoint = MatchableEndpoint(
            url_pattern=url_pattern,
            method=method,
            endpoint_function=endpoint_function,
        )
        cls._methods[method].append(matchable_endpoint)
        cls._methods[method].sort(
            key=lambda endpoint: len(endpoint.url_pattern), reverse=True
        )

    @classmethod
    def get(cls, url: str):
        """Decorator function to add endpoint to Handler"""

        def inner(endpoint_function: Callable):
            cls._add_endpoint(
                method="GET", url=url, endpoint_function=endpoint_function
            )
            return endpoint_function

        return inner

    @classmethod
    def post(cls, url: str):
        """Decorator function to add endpoint to Handler"""

        def inner(endpoint_function: Callable):
            cls._add_endpoint(
                method="POST", url=url, endpoint_function=endpoint_function
            )
            return endpoint_function

        return inner

    @classmethod
    def patch(cls, url: str):
        """Decorator function to add endpoint to Handler"""

        def inner(endpoint_function: Callable):
            cls._add_endpoint(
                method="PATCH", url=url, endpoint_function=endpoint_function
            )
            return endpoint_function

        return inner

    @staticmethod
    def _convert_parameter_types(
        endpoint_function: Callable,
        string_parameters: dict[str, str],
        request: httpx.Request,
    ) -> dict[str, Any]:
        """Get type info for function parameters. Since the values parsed from the URL
        are still in string format, cast them to the types specified in the signature.
        If the request is needed, include that in the returned parameters"""

        # Get the parameter information from the endpoint function signature
        signature_parameters = get_type_hints(endpoint_function)

        # type-cast based on type-hinting info
        typed_parameters: dict[str, Any] = {}
        for parameter_name, value in string_parameters.items():
            try:
                parameter_type = signature_parameters[parameter_name]

            # all parameters should be typed, raise exception otherwise
            except KeyError as err:
                raise TypeError(
                    f"Parameter '{parameter_name}' in function "
                    + f"'{endpoint_function.__name__}' is missing type information!"
                ) from err

            if parameter_type is not str:
                value = parameter_type(value)
            typed_parameters[parameter_name] = value

        # include request itself if needed (e.g. for header or auth info),
        if "request" in signature_parameters:
            typed_parameters["request"] = request

        logger.info("\tParameters are:")
        for name, value in typed_parameters.items():
            logger.info("\t\t%s: %s (%s)", name, value, type(value))

        return typed_parameters

    @classmethod
    def _get_function_and_parameters(
        cls, url: str, method: str
    ) -> tuple[Callable, dict[str, str]]:
        """Iterate through the registered endpoints for the given method.
        For each registered endpoint, try to match the request's url to the endpoint pattern.
        Upon matching, return the function and parsed variables from the url (if applicable).
        """
        for endpoint in cls._methods[method]:
            matched_url = re.search(endpoint.url_pattern, url)
            if matched_url:
                endpoint_function = endpoint.endpoint_function
                logger.info("\tGoing to call function: %s", endpoint_function.__name__)

                # return endpoint function with url-string parameters
                return (
                    endpoint_function,
                    matched_url.groupdict(),
                )

        logger.error("For %s, failed to match URL: `%s`", method, url)
        assert False

    @classmethod
    def build_loaded_endpoint_function(cls, request: httpx.Request) -> partial:
        """Route a request to the correct endpoint, build typed parameter dictionary,
        and return loaded partial func"""

        # get endpoint function and the parsed string parameters from the url
        endpoint_function, string_parameters = cls._get_function_and_parameters(
            url=str(request.url), method=request.method
        )

        # convert string parameters into the types specified in function signature
        typed_parameters = cls._convert_parameter_types(
            endpoint_function=endpoint_function,
            string_parameters=string_parameters,
            request=request,
        )

        # return function with the typed parameters
        return partial(endpoint_function, **typed_parameters)
