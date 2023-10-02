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

"""Tests for the MockRouter class."""

from typing import Union

import httpx
import pytest
from fastapi import HTTPException
from pytest_httpx import HTTPXMock, httpx_mock  # noqa: F401

from ghga_service_commons.api.mock_router import (  # noqa: F401
    MockRouter,
    assert_all_responses_were_requested,
)
from ghga_service_commons.httpyexpect.server.exceptions import HttpException
from tests.integration.fixtures.mock_api import app

BASE_URL = "http://localhost"


def http_exception_handler(request: httpx.Request, exc: HttpException):
    """Define an exception handler that can be attached to the MockRouter."""
    assert isinstance(exc, HttpException)
    return httpx.Response(
        status_code=exc.status_code,
        json=exc.body.dict(),
    )


def test_non_existent_path(httpx_mock: HTTPXMock):  # noqa: F811
    """Make a request with a path that isn't registered."""
    httpx_mock.add_callback(callback=app.handle_request)
    with pytest.raises(HttpException):
        with httpx.Client(base_url=BASE_URL) as client:
            client.get("/does/not/exist")


def test_url_with_wrong_method(httpx_mock: HTTPXMock):  # noqa: F811
    """Make a request to a url that is registered but with the wrong method."""
    httpx_mock.add_callback(callback=app.handle_request)
    with pytest.raises(HttpException):
        with httpx.Client(base_url=BASE_URL) as client:
            client.patch("/hello")


def test_simplest_get(httpx_mock: HTTPXMock):  # noqa: F811
    """Make sure there's nothing wrong with an endpoint path with no variables."""
    httpx_mock.add_callback(callback=app.handle_request)
    with httpx.Client(base_url=BASE_URL) as client:
        response = client.get("/hello")
        assert response is not None
        assert response.json() == {"hello": "world"}


def test_get_one_path_variable(httpx_mock: HTTPXMock):  # noqa: F811
    """Verify that a path terminating with one variable is okay."""
    httpx_mock.add_callback(callback=app.handle_request)

    expected = "beach_ball"

    with httpx.Client(base_url=BASE_URL) as client:
        response = client.get(f"/items/{expected}")
        assert response is not None
        body = response.json()
        assert "expected" in body
        assert body["expected"] == expected


def test_get_two_path_variables(httpx_mock: HTTPXMock):  # noqa: F811
    """Make sure the handler can parse paths with more than one variable."""
    httpx_mock.add_callback(callback=app.handle_request)

    expected = ["4", 9]  # pass str number as a sanity check that it stays a str

    with httpx.Client(base_url=BASE_URL) as client:
        response = client.get(f"/items/{expected[0]}/sizes/{expected[1]}")
        assert response is not None
        body = response.json()
        assert "expected" in body
        assert body["expected"] == expected


def test_get_with_bad_input(httpx_mock: HTTPXMock):  # noqa: F811
    """Look for error raised with invalid path variables."""
    httpx_mock.add_callback(callback=app.handle_request)

    expected = ["pass", "fail"]

    with pytest.raises(HttpException):
        with httpx.Client(base_url=BASE_URL) as client:
            client.get(f"/items/{expected[0]}/sizes/{expected[1]}")


def test_post_successful(httpx_mock: HTTPXMock):  # noqa: F811
    """Pass a vanilla POST request.

    Makes sure that the request parameter is correctly passed to the endpoint function.
    """
    httpx_mock.add_callback(callback=app.handle_request)

    request_body = {"detail": {"a key": "a value"}}
    expected = request_body["detail"]

    with httpx.Client(base_url=BASE_URL) as client:
        response = client.post("/items", json=request_body)
        assert response is not None

        body = response.json()
        assert "expected" in body
        assert body["expected"] == expected


def test_post_failure(httpx_mock: HTTPXMock):  # noqa: F811
    """Cause the endpoint to raise an HttpException.

    Makes sure that endpoint-defined exceptions are passed up as expected when no
    exception handler is specified.
    """
    httpx_mock.add_callback(callback=app.handle_request)

    # cause a failure by omitting the "detail" key that the endpoint looks for
    with pytest.raises(HttpException):
        with httpx.Client(base_url=BASE_URL) as client:
            client.post("/items", json={})


def test_post_failure_with_handler(httpx_mock: HTTPXMock):  # noqa: F811
    """Cause the endpoint to raise an HttpException.

    Makes sure that exceptions are handled with the specified handler.
    """
    app.exception_handler = http_exception_handler
    httpx_mock.add_callback(callback=app.handle_request)

    # cause a failure by omitting the "detail" key that the endpoint looks for
    with httpx.Client(base_url=BASE_URL) as client:
        client.post("/items", json={})


def test_path_and_function_mismatch():
    """Test endpoint decorators.

    Make sure that we get an error if path variable names and decorated endpoint
    function parameter names are not identical.
    """
    # create a new MockRouter so we don't modify 'app'
    throwaway: MockRouter = MockRouter()

    with pytest.raises(
        TypeError,
        match="Path variables for path '/dummy/{pram1}' do not match the function it decorates",
    ):

        @throwaway.get("/dummy/{pram1}")
        def dummy(parameter1: int) -> None:
            """Define a dummy function with parameter mismatch."""


def test_endpoint_missing_typehint():
    """Make sure that we get an error when a registered endpoint lacks type hints."""
    # create a new MockRouter so we don't modify 'app'
    throwaway: MockRouter = MockRouter()

    with pytest.raises(
        TypeError,
        match="Parameter 'parameter1' in 'dummy' is missing a type hint",
    ):

        @throwaway.get("/dummy/{parameter1}")
        def dummy(parameter1) -> None:
            """Define a dummy function with missing type-hint info."""


def test_handler_errors_filtering(httpx_mock: HTTPXMock):  # noqa: F811
    """Make sure only the specified errors are passed to the handler.

    When a handler is provided and errors are specified,
    all other types should be raised again.
    """

    class TestValueError(ValueError):
        """Subclass of ValueError to test handle_exception_subclasses."""

    def handler(request: httpx.Request, exc: Union[ValueError, TestValueError]):
        return httpx.Response(status_code=500)

    throwaway: MockRouter = MockRouter(
        exception_handler=handler,
        exceptions_to_handle=(ValueError,),
    )

    @throwaway.get("/gotohandler")
    def succeeds():
        raise ValueError()  # will get passed to handler

    @throwaway.get("/raise")
    def fails():
        raise HttpException(  # won't get passed to handler and will thus be re-raised
            status_code=404, exception_id="test", description="test", data={}
        )

    @throwaway.get("/raise2")
    def fails_also():  # will only get passed to error if we set handle_exception_subclasses
        raise TestValueError()

    httpx_mock.add_callback(callback=throwaway.handle_request)

    with httpx.Client(base_url=BASE_URL) as client:
        client.get("/gotohandler")
        with pytest.raises(HttpException):
            client.get("/raise")
        with pytest.raises(TestValueError):
            client.get("/raise2")

        throwaway.handle_exception_subclasses = True
        client.get("/raise2")


def test_exceptions_no_handler(httpx_mock: HTTPXMock):  # noqa: F811
    """Test exception handlers.

    Errors specified in exceptions_to_handle should be raised normally if
    exception_handler is not defined.
    """
    throwaway: MockRouter = MockRouter(
        exceptions_to_handle=(HttpException, HTTPException)
    )

    @throwaway.get("/")
    def raise_an_error():
        raise HTTPException(status_code=404)

    httpx_mock.add_callback(callback=throwaway.handle_request)

    with httpx.Client(base_url=BASE_URL) as client:
        with pytest.raises(HTTPException):
            client.get("/")


def test_no_exceptions_specified(httpx_mock: HTTPXMock):  # noqa: F811
    """Make sure nothing is passed to the error handler if we omit exceptions_to_handle."""

    def handler(request: httpx.Request, exc: HTTPException):
        return httpx.Response(status_code=500)

    throwaway: MockRouter = MockRouter(exception_handler=handler)

    @throwaway.get("/")
    def raise_an_error():
        raise HTTPException(status_code=404)

    httpx_mock.add_callback(callback=throwaway.handle_request)

    with httpx.Client(base_url=BASE_URL) as client:
        with pytest.raises(HTTPException):
            client.get("/")
