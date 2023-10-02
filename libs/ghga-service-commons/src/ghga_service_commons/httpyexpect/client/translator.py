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

"""Logic to translate responses to HTTP calls to python exceptions."""

from typing import Optional

import pydantic

from ghga_service_commons.httpyexpect.client.custom_types import Response
from ghga_service_commons.httpyexpect.client.exceptions import UnstructuredError
from ghga_service_commons.httpyexpect.client.mapping import ExceptionMapping
from ghga_service_commons.httpyexpect.models import HttpExceptionBody
from ghga_service_commons.httpyexpect.validation import (
    ValidationError,
    assert_error_code,
)


class ResponseTranslator:
    """Translate a specific response to an HTTP call.

    Use ExceptionMapping to translate to python exception (in case of an error code).
    """

    def __init__(self, response: Response, *, exception_map: ExceptionMapping):
        """Initialize the translator.

        Args:
            response:
                A response to an HTTP call performed e.g. with the `httpx` or `requests`
                library.
            exception_map:
                An exception mapping specifying translations between status codes plus
                exception IDs and python exceptions.
        """
        self._exception_map = exception_map
        self._response = response

    @staticmethod
    def _get_validated_exception_body(response: Response) -> HttpExceptionBody:
        """Validate the response body against the HttpyExceptionBody model."""
        body = response.json()
        try:
            return HttpExceptionBody(**body)
        except pydantic.ValidationError as error:
            raise UnstructuredError(
                status_code=response.status_code, body=body
            ) from error

    @classmethod
    def _construct_exception(
        cls, response: Response, exception_map: ExceptionMapping
    ) -> Exception:
        """Construct a python exception from a response."""
        # validate and parse the body of the exception response:
        body = cls._get_validated_exception_body(response)

        # get a factory kit that ships the exception factory together with instructions
        # on how to use it:
        factory_kit = exception_map.get_factory_kit(
            status_code=response.status_code, exception_id=body.exception_id
        )

        # assembled the required parameter values:
        param_values = {
            "status_code": response.status_code,
            "exception_id": body.exception_id,
            "description": body.description,
            "data": body.data,
        }
        required_param_values = {
            key: value
            for key, value in param_values.items()
            if key in factory_kit.required_params
        }

        # call the factory with the param values to get the exception:
        return factory_kit.factory(**required_param_values)

    def get_error(self) -> Optional[Exception]:
        """Translate the response into a python exception.

        In case the provided response corresponds to an error, it will translate the
        response into a python exception and return it.
        Please note, this function will only return exceptions but not raise them.

        Returns:
            A python exception in case of an HTTP error, `None` otherwise.
        """
        try:
            assert_error_code(self._response.status_code)
        except ValidationError:
            # The response doesn't correspond to an exception:
            return None

        return self._construct_exception(
            response=self._response, exception_map=self._exception_map
        )

    def raise_for_error(self):
        """Translate response into python exception.

        In case the provided response corresponds to an error, it will translate the
        response into a python exception and raise it. Otherwise, nothing happens.
        """
        exception = self.get_error()
        if exception is not None:
            raise exception
