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

"""Tests for the MockRouter class."""

from __future__ import annotations

import httpx2
import pytest
from fastapi import HTTPException

from ghga_service_commons.api.mock_router import MockRouter
from ghga_service_commons.httpyexpect.server.exceptions import HttpException
from tests.integration.fixtures.mock_api import app

BASE_URL = "http://localhost"


def http_exception_handler(request: httpx2.Request, exc: HttpException):
    """Define an exception handler that can be attached to the MockRouter."""
    assert isinstance(exc, HttpException)
    return httpx2.Response(
        status_code=exc.status_code,
        json=exc.body.model_dump(),
    )


def test_non_existent_path():
    """Make a request with a path that isn't registered."""
    with pytest.raises(HttpException):
        with httpx2.Client(base_url=BASE_URL, transport=app.as_transport()) as client:
            client.get("/does/not/exist")


def test_url_with_wrong_method():
    """Make a request to a url that is registered but with the wrong method."""
    with pytest.raises(HttpException):
        with httpx2.Client(base_url=BASE_URL, transport=app.as_transport()) as client:
            client.patch("/hello")


def test_simplest_get():
    """Make sure there's nothing wrong with an endpoint path with no variables."""
    with httpx2.Client(base_url=BASE_URL, transport=app.as_transport()) as client:
        response = client.get("/hello")
        assert response is not None
        assert response.json() == {"hello": "world"}


def test_get_one_path_variable():
    """Verify that a path terminating with one variable is okay."""
    expected = "beach_ball"

    with httpx2.Client(base_url=BASE_URL, transport=app.as_transport()) as client:
        response = client.get(f"/items/{expected}")
        assert response is not None
        body = response.json()
        assert "expected" in body
        assert body["expected"] == expected


def test_get_two_path_variables():
    """Make sure the handler can parse paths with more than one variable."""
    # pass str number as a sanity check that it stays a str
    expected = ["4", 9]

    with httpx2.Client(base_url=BASE_URL, transport=app.as_transport()) as client:
        response = client.get(f"/items/{expected[0]}/sizes/{expected[1]}")
        assert response is not None
        body = response.json()
        assert "expected" in body
        assert body["expected"] == expected


def test_get_with_bad_input():
    """Look for error raised with invalid path variables."""
    expected = ["pass", "fail"]

    with pytest.raises(HttpException):
        with httpx2.Client(base_url=BASE_URL, transport=app.as_transport()) as client:
            client.get(f"/items/{expected[0]}/sizes/{expected[1]}")


def test_post_successful():
    """Pass a vanilla POST request.

    Makes sure that the request parameter is correctly passed to the endpoint function.
    """
    request_body = {"detail": {"a key": "a value"}}
    expected = request_body["detail"]

    with httpx2.Client(base_url=BASE_URL, transport=app.as_transport()) as client:
        response = client.post("/items", json=request_body)
        assert response is not None

        body = response.json()
        assert "expected" in body
        assert body["expected"] == expected


def test_post_failure():
    """Cause the endpoint to raise an HttpException.

    Makes sure that endpoint-defined exceptions are passed up as expected when no
    exception handler is specified.
    """
    # cause a failure by omitting the "detail" key that the endpoint looks for
    with pytest.raises(HttpException):
        with httpx2.Client(base_url=BASE_URL, transport=app.as_transport()) as client:
            client.post("/items", json={})


def test_post_failure_with_handler():
    """Cause the endpoint to raise an HttpException.

    Makes sure that exceptions are handled with the specified handler.
    """
    app.exception_handler = http_exception_handler

    # cause a failure by omitting the "detail" key that the endpoint looks for
    with httpx2.Client(base_url=BASE_URL, transport=app.as_transport()) as client:
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
        match=r"Path variables for path '/dummy/{p2}' do not match the function it decorates",
    ):

        @throwaway.get("/dummy/{p2}")
        def dummy(p1: int) -> None:
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


def test_query_string_is_left_out_of_the_matching():
    """Make sure an endpoint is found whether or not the call carries a query string."""
    throwaway: MockRouter = MockRouter()

    @throwaway.get("/items/{item_name}")
    def get_item(item_name: str) -> httpx2.Response:
        """Report back the item name the path was matched with."""
        return httpx2.Response(status_code=200, json={"expected": item_name})

    with httpx2.Client(base_url=BASE_URL, transport=throwaway.as_transport()) as client:
        # without the query being left out, the pattern's trailing group would swallow
        # it and the endpoint would report an item name of "ball?size=large"
        response = client.get("/items/ball?size=large")

    assert response.json() == {"expected": "ball"}


def test_endpoint_collecting_path_variables():
    """Make sure one function can serve endpoints with differing path variables."""
    throwaway: MockRouter = MockRouter()

    def endpoint(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        """Report back whatever path variables the endpoint was called with."""
        return httpx2.Response(status_code=200, json=path_variables)

    throwaway.get("/items/{item_name}")(endpoint)
    throwaway.get("/items/{item_name}/sizes/{item_size}")(endpoint)
    throwaway.get("/items")(endpoint)

    with httpx2.Client(base_url=BASE_URL, transport=throwaway.as_transport()) as client:
        assert client.get("/items/ball").json() == {"item_name": "ball"}
        assert client.get("/items/ball/sizes/9").json() == {
            "item_name": "ball",
            "item_size": "9",
        }
        assert client.get("/items").json() == {}


def test_endpoint_naming_a_variable_the_path_does_not_have():
    """Make sure collecting the rest still requires the named variables to exist."""
    throwaway: MockRouter = MockRouter()

    with pytest.raises(
        TypeError,
        match=r"Path variables for path '/dummy/{p2}' do not match the function it decorates",
    ):

        @throwaway.get("/dummy/{p2}")
        def dummy(p1: int, **path_variables: str) -> None:
            """Define a dummy function naming a variable that the path lacks."""


def test_path_variables_the_endpoint_does_not_name_are_rejected():
    """Ensure a path variable no parameter takes is rejected."""
    throwaway: MockRouter = MockRouter()
    mismatch = r"Path variables for path '/items/{item_name}' do not match"

    with pytest.raises(TypeError, match=mismatch):

        @throwaway.get("/items/{item_name}")
        def takes_nothing() -> None:
            """Take no arguments at all."""

    with pytest.raises(TypeError, match=mismatch):

        @throwaway.get("/items/{item_name}")
        def takes_only_the_request(request: httpx2.Request) -> None:
            """Take the request, but still no item name."""


def test_handler_errors_filtering():
    """Make sure only the specified errors are passed to the handler.

    When a handler is provided and errors are specified,
    all other types should be raised again.
    """

    class TestValueError(ValueError):
        """Subclass of ValueError to test handle_exception_subclasses."""

    def handler(request: httpx2.Request, exc: ValueError | TestValueError):
        return httpx2.Response(status_code=500)

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

    with httpx2.Client(base_url=BASE_URL, transport=throwaway.as_transport()) as client:
        client.get("/gotohandler")
        with pytest.raises(HttpException):
            client.get("/raise")
        with pytest.raises(TestValueError):
            client.get("/raise2")

        throwaway.handle_exception_subclasses = True
        client.get("/raise2")


def test_exceptions_no_handler():
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

    with httpx2.Client(base_url=BASE_URL, transport=throwaway.as_transport()) as client:
        with pytest.raises(HTTPException):
            client.get("/")


def test_no_exceptions_specified():
    """Make sure nothing is passed to the error handler if we omit exceptions_to_handle."""

    def handler(request: httpx2.Request, exc: HTTPException):
        return httpx2.Response(status_code=500)

    throwaway: MockRouter = MockRouter(exception_handler=handler)

    @throwaway.get("/")
    def raise_an_error():
        raise HTTPException(status_code=404)

    with httpx2.Client(base_url=BASE_URL, transport=throwaway.as_transport()) as client:
        with pytest.raises(HTTPException):
            client.get("/")
