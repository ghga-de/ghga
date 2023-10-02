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

"""Test the mapping module."""

from contextlib import nullcontext

import pytest

from ghga_service_commons.httpyexpect.client.custom_types import (
    ExceptionFactory,
    ExceptionFactoryParam,
    ExceptionMappingSpec,
)
from ghga_service_commons.httpyexpect.client.mapping import (
    ExceptionMapping,
    ValidationError,
)


class ExampleError(RuntimeError):
    """A exception return or thrown as part of a test."""

    def __init__(self):
        """Initialize without args."""
        super().__init__()


class ExampleWithArgsError(RuntimeError):
    """A exception return or thrown as part of a test."""

    def __init__(
        self, status_code: int, exception_id: str, description: str, data: dict
    ):
        """Initialize the error with the required metadata."""
        super().__init__()


@pytest.mark.parametrize(
    "spec, is_valid",
    [
        # a spec containing multiple valid scenarios:
        (
            {
                400: {
                    "myTestException0": lambda status_code, exception_id, description, data: ExampleError(),
                    "myTestException1": lambda exception_id, description, data: ExampleError(),
                    "myTestException2": lambda status_code, data: ExampleError(),
                },
                403: {
                    "myTestException3": lambda exception_id, description: ExampleError(),
                    "myTestException4": lambda exception_id, data: ExampleError(),
                },
                404: {
                    "myTestException5": lambda description, data: ExampleError(),
                    "myTestException6": lambda exception_id: ExampleError(),
                },
                427: {
                    "myTestException7": lambda description: ExampleError(),
                    "myTestException8": lambda data: ExampleError(),
                    "myTestException9": lambda status_code: ExampleError(),
                },
                500: {
                    "myTestException10": lambda: ExampleError(),
                    "myTestException11": ExampleError,
                    "myTestException12": ExampleWithArgsError,
                },
            },
            True,
        ),
        # invalid status codes:
        (
            {-100: {"myTestException": lambda exception_id: ExampleError()}},
            False,
        ),
        (
            {100: {"myTestException": lambda exception_id: ExampleError()}},
            False,
        ),
        (
            {200: {"myTestException": lambda exception_id: ExampleError()}},
            False,
        ),
        (
            {300: {"myTestException": lambda exception_id: ExampleError()}},
            False,
        ),
        (
            {600: {"myTestException": lambda exception_id: ExampleError()}},
            False,
        ),
        # invalid exception ids:
        (
            {400: {"myTeßtException": lambda exception_id: ExampleError()}},
            False,
        ),
        (
            {400: {"1myTestException": lambda exception_id: ExampleError()}},
            False,
        ),
        (
            {400: {"mt": lambda exception_id: ExampleError()}},
            False,
        ),
        # invalid exception factories:
        (
            {400: {"myTestException": ExampleError()}},
            False,
        ),
        (
            {400: {"myTestException": 123}},
            False,
        ),
        # spec is not a mapping:
        (
            {400: lambda exception_id: ExampleError()},
            False,
        ),
        # exception factory has unexpected parameters:
        (
            {400: {"myTestException": lambda foo: ExampleError()}},
            False,
        ),
        (
            {400: {"myTestException": lambda exception_id, foo: ExampleError()}},
            False,
        ),
        (
            {400: {"myTestException": lambda exception_id, foo="foo": ExampleError()}},
            False,
        ),
        # exception factory uses variadic args/kwargs (e.g. *arg **kwargs):
        (
            {400: {"myTestException": lambda exception_id, *foo: ExampleError()}},
            False,
        ),
        (
            {400: {"myTestException": lambda exception_id, **bar: ExampleError()}},
            False,
        ),
        (
            {400: {"myTestException": RuntimeError}},
            False,
        ),
        # exception factory with wrong parameter orders:
        (
            {
                400: {
                    "myTestException": lambda exception_id, status_code: ExampleError()
                }
            },
            False,
        ),
        (
            {400: {"myTestException": lambda data, description: ExampleError()}},
            False,
        ),
    ],
)
def test_exception_mapping_validation(spec: ExceptionMappingSpec, is_valid: bool):
    """Test the ExceptionMappingSpec validation from the ExceptionMapping class."""
    with nullcontext() if is_valid else pytest.raises(ValidationError):
        ExceptionMapping(spec)


@pytest.mark.parametrize(
    "fallback_factory, is_valid",
    [
        (lambda status_code, exception_id, description, data: ExampleError(), True),
        (lambda status_code, data: ExampleError(), True),
        (ExampleWithArgsError, True),
        (123, False),
        (lambda foo: ExampleError(), False),
        (lambda data, description: ExampleError(), False),
    ],
)
def test_fallback_factory_validation(fallback_factory: object, is_valid: bool):
    """Test the ExceptionMappingSpec behavior for validating fallback factories."""
    with nullcontext() if is_valid else pytest.raises(ValidationError):
        ExceptionMapping({}, fallback_factory=fallback_factory)  # type: ignore


@pytest.mark.parametrize(
    "factory, expected_params",
    [
        (
            lambda status_code, exception_id, description, data: ExampleError(),
            ["status_code", "exception_id", "description", "data"],
        ),
        (lambda status_code, data: ExampleError(), ["status_code", "data"]),
        (lambda: ExampleError(), []),
    ],
)
def test_get_factory_kit(
    factory: ExceptionFactory, expected_params: list[ExceptionFactoryParam]
):
    """Test the `get_factory_kit` method of the `ExceptionMapping` class."""
    # build a spec around the provided factory:
    status_code = 400
    exception_id = "myTestException"
    spec = {status_code: {exception_id: factory}}

    # create an ExceptionMapping and get a factory kit:
    mapping = ExceptionMapping(spec)
    factory_kit = mapping.get_factory_kit(
        status_code=status_code, exception_id=exception_id
    )

    # check the returned FactoryKit:
    assert factory_kit.factory == factory
    assert factory_kit.required_params == expected_params


def test_get_factory_kit_not_existent():
    """Test the `get_factory_kit` method of the `ExceptionMapping` class.

    Test the `get_factory_kit` method of the `ExceptionMapping` class
    when called with parameters that don't resolve to a mapping.
    """
    fallback_factory = lambda status_code, data: ExampleError()
    expected_params = ["status_code", "data"]

    # create an ExceptionMapping and get a factory kit:
    mapping = ExceptionMapping(spec={}, fallback_factory=fallback_factory)
    factory_kit = mapping.get_factory_kit(
        status_code=400, exception_id="myTestException"
    )

    # check the returned FactoryKit:
    assert factory_kit.factory == fallback_factory
    assert factory_kit.required_params == expected_params
