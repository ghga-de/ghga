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

"""Testing the MockedApi from the api subpackage."""

import httpx2
import pytest

from ghga_service_commons.api.mock_api import (
    MockedApi,
    MockSetupError,
    NotMockedError,
    endpoint,
)


def test_endpoints_serving_the_same_route_are_rejected():
    """Test that two endpoints for one method and path fail when the mock is built.

    The second spells the route differently, which `Endpoint` normalizes to the same.
    """

    class MockedDuplicateApi(MockedApi):
        base_url = "http://duplicate.test"
        on_first = endpoint("GET", "/things")
        on_second = endpoint("get", "things")

    with pytest.raises(
        MockSetupError, match=r"GET /things as both 'on_first' and 'on_second'"
    ):
        MockedDuplicateApi()


def test_other_methods_and_overrides_are_not_duplicates():
    """Test that other methods on one path, and a subclass override, are allowed."""

    class MockedBaseApi(MockedApi):
        base_url = "http://distinct.test"
        on_get_thing = endpoint("GET", "/things/{thing_id}")
        on_delete_thing = endpoint("DELETE", "/things/{thing_id}")

    class MockedSubApi(MockedBaseApi):
        on_get_thing = endpoint("GET", "/things/{thing_id}")

    MockedBaseApi()
    MockedSubApi()


class MockedWildcardApi(MockedApi):
    """A base mock whose wildcard route also matches the subclass routes."""

    base_url = "http://things.test"
    on_any_thing = endpoint(
        "GET",
        "/things/{thing_id}",
        lambda request, **kw: httpx2.Response(200, text="any"),
    )
    on_health = endpoint(
        "GET", "/health", lambda request, **kw: httpx2.Response(200, text="base")
    )


class MockedSpecificApi(MockedWildcardApi):
    """A subclass adding a specific route and redeclaring `on_health`."""

    on_latest_thing = endpoint(
        "GET",
        "/things/latest",
        lambda request, **kw: httpx2.Response(200, text="latest"),
    )
    on_health = endpoint(
        "GET", "/status", lambda request, **kw: httpx2.Response(200, text="sub")
    )


def _as_transport(mock: MockedApi) -> httpx2.MockTransport:
    """Mount `mock` by hand, since `MockedApi` does not offer a transport itself."""

    def answer(request: httpx2.Request) -> httpx2.Response:
        path = mock._path_relative_to_base_url(request.url)
        assert path is not None
        return mock._answer(request, path)

    return httpx2.MockTransport(answer)


def test_subclass_routes_are_tried_before_base_routes():
    """Test that a subclass route wins over a base route that also matches the path."""
    mock = MockedSpecificApi()
    with httpx2.Client(base_url=mock.base_url, transport=_as_transport(mock)) as client:
        assert client.get("/things/latest").text == "latest"
        assert client.get("/things/other").text == "any"


def test_subclass_endpoint_replaces_base_endpoint_of_same_name():
    """Test that redeclaring an endpoint name in a subclass serves only the new route."""
    mock = MockedSpecificApi()
    with httpx2.Client(base_url=mock.base_url, transport=_as_transport(mock)) as client:
        assert client.get("/status").text == "sub"
        with pytest.raises(NotMockedError):
            client.get("/health")


class MockedPositionalApi(MockedApi):
    """A mock whose handlers take their parameters positionally in different ways."""

    base_url = "http://positional.test"

    @endpoint("GET", "/positional/{thing_id}")
    def on_positional(
        self, request: httpx2.Request, thing_id: int, /
    ) -> httpx2.Response:
        """Take the path variable only positionally, which it cannot be passed as."""
        return httpx2.Response(200, text=str(thing_id))

    @endpoint("GET", "/named/{thing_id}")
    def on_named(self, request: httpx2.Request, /, thing_id: int) -> httpx2.Response:
        """Take only the request positionally, and the path variable by name."""
        return httpx2.Response(200, text=str(thing_id))

    # the request slot is positional whatever it is called, so this must keep working
    on_renamed_request = endpoint(
        "GET",
        "/renamed/{thing_id}",
        lambda req, /, **kw: httpx2.Response(200, text=kw["thing_id"]),
    )


def test_path_variables_are_never_bound_to_positional_only_parameters():
    """Test that a path variable aimed at a positional-only parameter is a setup error.

    Only a path variable that names such a parameter fails; a positional-only request
    slot, under any name, still works.
    """
    mock = MockedPositionalApi()
    with httpx2.Client(base_url=mock.base_url, transport=_as_transport(mock)) as client:
        with pytest.raises(MockSetupError, match=r"takes 'thing_id' positionally only"):
            client.get("/positional/3")
        assert client.get("/named/3").text == "3"
        assert client.get("/renamed/3").text == "3"


class MockedFlagApi(MockedApi):
    """A mock whose handler takes a boolean path variable."""

    base_url = "http://flags.test"

    @endpoint("GET", "/flags/{flag}")
    def on_flag(self, request: httpx2.Request, *, flag: bool) -> httpx2.Response:
        """Echo the flag as the handler received it."""
        return httpx2.Response(200, json={"flag": flag})


@pytest.mark.parametrize(
    ("spelling", "expected"),
    [
        *[
            (spelling, True)
            for spelling in ("true", "TRUE", "1", "yes", "on", "t", "Y")
        ],
        *[
            (spelling, False)
            for spelling in ("false", "False", "0", "no", "off", "F", "n")
        ],
    ],
)
def test_bool_path_variables_read_like_fastapi(spelling: str, expected: bool):
    """Test that boolean path vars are parsed correctly."""
    mock = MockedFlagApi()
    with httpx2.Client(base_url=mock.base_url, transport=_as_transport(mock)) as client:
        assert client.get(f"/flags/{spelling}").json() == {"flag": expected}


@pytest.mark.parametrize("spelling", ["maybe", "2", "1.0"])
def test_other_bool_spellings_are_a_422(spelling: str):
    """Test some non-boolean values and make sure they trigger a 422."""
    mock = MockedFlagApi()
    with httpx2.Client(base_url=mock.base_url, transport=_as_transport(mock)) as client:
        response = client.get(f"/flags/{spelling}")
    assert response.status_code == 422
    assert response.json()["exception_id"] == "malformedUrl"


class MockedMissingVariableApi(MockedApi):
    """A mock whose handlers take parameters their endpoints' paths do not declare."""

    base_url = "http://missing.test"

    @endpoint("GET", "/things")
    def on_things(self, request: httpx2.Request, *, thing_id: int) -> httpx2.Response:
        """Need a `thing_id` the path never supplies."""
        return httpx2.Response(200)

    @endpoint("GET", "/pages")
    def on_pages(self, request: httpx2.Request, *, page: int = 1) -> httpx2.Response:
        """Take a `page` the path never supplies, but that has a default."""
        return httpx2.Response(200, text=str(page))


def test_handler_parameter_missing_from_the_path_is_a_setup_error():
    """Test that a required parameter no path variable fills is a setup error.

    A parameter with a default is not required, so the path may leave it out.
    """
    mock = MockedMissingVariableApi()
    with httpx2.Client(base_url=mock.base_url, transport=_as_transport(mock)) as client:
        with pytest.raises(
            MockSetupError,
            match=r"needs 'thing_id', which the endpoint's path does not",
        ):
            client.get("/things")
        assert client.get("/pages").text == "1"
