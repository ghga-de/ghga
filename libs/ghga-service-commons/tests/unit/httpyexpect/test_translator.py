# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the `translator` module."""

from collections.abc import Callable, Sequence
from typing import NamedTuple
from unittest.mock import Mock

import pytest

from ghga_service_commons.httpyexpect.client.exceptions import UnstructuredError
from ghga_service_commons.httpyexpect.client.mapping import (
    EXCEPTION_FACTORY_PARAMS,
    FactoryKit,
)
from ghga_service_commons.httpyexpect.client.translator import ResponseTranslator
from ghga_service_commons.httpyexpect.models import HttpExceptionBody


class ExampleError(RuntimeError):
    """A exception that save all its input params."""

    def __init__(self, *params):
        """Initialize the error with the some params."""
        self.params = params
        super().__init__()


class Case(NamedTuple):
    """Data for a test case to use with `test_response_translator_success`."""

    status_code: int
    exception_id: str
    description: str
    data: dict
    exception_factory: Callable
    required_params: Sequence


@pytest.mark.parametrize(
    "case",
    [
        # use all possible parameters in the factory:
        Case(
            status_code=400,
            exception_id="myTestException",
            description="Test error.",
            data={"test": "test"},
            exception_factory=lambda status_code,
            exception_id,
            description,
            data: ExampleError(status_code, exception_id, description, data),
            required_params=EXCEPTION_FACTORY_PARAMS,
        ),
        # only use some parameters in the factory:
        Case(
            status_code=400,
            exception_id="myTestException",
            description="Test error.",
            data={"test": "test"},
            exception_factory=lambda status_code, data: ExampleError(status_code, data),
            required_params=["status_code", "data"],
        ),
    ],
)
def test_response_translator_error(case: Case):
    """Test the `ResponseTranslator`.

    Test that the translator can interpret a mapping and an error response
    correctly to translate it into a python exception.
    """
    all_params = {
        "status_code": case.status_code,
        "exception_id": case.exception_id,
        "description": case.description,
        "data": case.data,
    }
    required_param_values = [
        value for key, value in all_params.items() if key in case.required_params
    ]
    expected_exception = ExampleError(*required_param_values)

    # create exception mapping mock:
    exception_map = Mock()
    exception_map.get_factory_kit.return_value = FactoryKit(
        factory=case.exception_factory, required_params=case.required_params
    )

    # create http response mock:
    body = HttpExceptionBody(
        exception_id=case.exception_id, description=case.description, data=case.data
    )
    response = Mock()
    response.status_code = case.status_code
    response.json.return_value = body.model_dump()

    # initialize the ResponseTranslator:
    translator = ResponseTranslator(response, exception_map=exception_map)

    # translate and get the python exception object:
    obtained_exception = translator.get_error()
    assert isinstance(obtained_exception, ExampleError)
    assert obtained_exception.params == expected_exception.params

    # translate into python exception and raise it:
    with pytest.raises(ExampleError):
        translator.raise_for_error()


@pytest.mark.parametrize("status_code", [100, 200, 300])
def test_response_translator_no_error(status_code: int):
    """Test the behavior of `ResponseTranslator`.

    Test for when the response does not correspond
    to a exception (e.g. 200 response code).
    """
    # create http response mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = {"Hello": "World"}

    # initialize the ResponseTranslator:
    translator = ResponseTranslator(response, exception_map=Mock())

    # translate and get a python exception object:
    obtained_exception = translator.get_error()
    assert obtained_exception is None

    # translate into python exception and raise it (no exception expected):
    translator.raise_for_error()


@pytest.mark.parametrize(
    "body",
    (
        # expected parameter missing:
        {"Hello": "World"},
        # expected parameters partially missing:
        {"description": "My test description.", "data": {"test": "test"}},
        # parameter values invalid (here: exception_id):
        {
            "exception_id": "123testException",
            "description": "My test description.",
            "data": {"test": "test"},
        },
    ),
)
def test_response_translator_unstructured(body: dict):
    """Test the `ResponseTranslator`.

    Test receiving a response that does not conform
    to the expected http exception body model.
    """
    status_code = 400
    # create http response mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = body

    # initialize the ResponseTranslator:
    translator = ResponseTranslator(response, exception_map=Mock())

    # translate and get a python exception object:
    with pytest.raises(UnstructuredError) as error_a:
        _ = translator.get_error()
    assert error_a.value.body == body

    # translate into python exception and raise it:
    with pytest.raises(UnstructuredError) as error_b:
        translator.raise_for_error()
    assert error_b.value.body == body
