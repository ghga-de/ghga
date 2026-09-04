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

"""Tests for the API mocks built on top of the MockRouter."""

from typing import Any

import httpx2
import pytest

from ghga_service_commons.api.mock_api import (
    ApiMock,
    endpoint,
    fail_to_connect,
    fail_with,
    httpyexpect_body,
    httpyexpect_error_handler,
    in_sequence,
    respond,
    unconfigured,
)
from ghga_service_commons.api.mock_router import MockRouter
from ghga_service_commons.httpyexpect.server.exceptions import HttpException

BASE_URL = "http://secrets.test/api"
OTHER_URL = "http://boxes.test"


class SecretsApiMock(ApiMock):
    """A mock of a small API, as a service would model the ones it calls."""

    on_get_secret = endpoint("GET", "/secrets/{secret_id}", respond(200, json="s3cret"))
    on_delete_secret = endpoint("DELETE", "/secrets/{secret_id}", respond(204))
    on_deposit_secret = endpoint("POST", "/secrets")

    def __init__(self, **kwargs: Any) -> None:
        """Serve the API at its usual base URL unless told otherwise."""
        kwargs.setdefault("base_url", BASE_URL)
        super().__init__(**kwargs)


class BoxesApiMock(ApiMock):
    """A mock of a second API, to test routing between them."""

    on_get_box = endpoint("GET", "/boxes/{box_id}", respond(200, json={"id": "box"}))


@pytest.fixture(name="secrets")
def secrets_fixture() -> SecretsApiMock:
    """Get a mock of the secrets API."""
    return SecretsApiMock()


def test_endpoints_answer_with_their_defaults(secrets: SecretsApiMock):
    """An endpoint that a test says nothing about answers with its default."""
    with httpx2.Client(transport=secrets.as_transport()) as client:
        response = client.get(f"{BASE_URL}/secrets/some-id")
        assert response.status_code == 200
        assert response.json() == "s3cret"
        assert client.delete(f"{BASE_URL}/secrets/some-id").status_code == 204


def test_assigned_handler_takes_over(secrets: SecretsApiMock):
    """Assigning a handler changes how the endpoint answers the calls that follow."""
    with httpx2.Client(transport=secrets.as_transport()) as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 200

        secrets.on_get_secret = respond(500)
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 500


def test_handlers_do_not_leak_between_instances(secrets: SecretsApiMock):
    """A handler assigned to one mock does not leak into the next one."""
    secrets.on_get_secret = respond(500)

    with httpx2.Client(transport=SecretsApiMock().as_transport()) as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 200


def test_endpoint_without_default_refuses(secrets: SecretsApiMock):
    """An endpoint declared without a default does not make up a response."""
    with httpx2.Client(transport=secrets.as_transport()) as client:
        with pytest.raises(AssertionError, match="`on_deposit_secret`"):
            client.post(f"{BASE_URL}/secrets", json={})

        secrets.on_deposit_secret = respond(201, json={"secret_id": "some-id"})
        assert client.post(f"{BASE_URL}/secrets", json={}).status_code == 201


def test_requests_are_recorded(secrets: SecretsApiMock):
    """Every request that reaches the mock is recorded, in order."""
    with httpx2.Client(transport=secrets.as_transport()) as client:
        client.get(f"{BASE_URL}/secrets/first")
        client.get(f"{BASE_URL}/secrets/second")

    assert len(secrets.requests) == 2
    assert str(secrets.last_request.url) == f"{BASE_URL}/secrets/second"


def test_last_request_without_any_request(secrets: SecretsApiMock):
    """Asking for the last request before there is one says which mock is meant."""
    with pytest.raises(AssertionError, match="No request reached the SecretsApiMock"):
        secrets.last_request  # noqa: B018


def test_path_variables_reach_the_handler(secrets: SecretsApiMock):
    """The handler is passed the path variables of the endpoint it answers."""
    seen: dict[str, str] = {}

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        seen.update(path_variables)
        return httpx2.Response(200)

    secrets.on_get_secret = handler

    with httpx2.Client(transport=secrets.as_transport()) as client:
        client.get(f"{BASE_URL}/secrets/some-id")

    assert seen == {"secret_id": "some-id"}


def test_query_string_does_not_hide_the_endpoint(secrets: SecretsApiMock):
    """An endpoint serves the calls to its path whether they carry a query or not."""
    with httpx2.Client(transport=secrets.as_transport()) as client:
        response = client.get(f"{BASE_URL}/secrets/some-id?public_key=abc")

    assert response.status_code == 200
    assert secrets.last_request.url.params["public_key"] == "abc"


def test_requests_to_another_api_are_not_answered(secrets: SecretsApiMock):
    """A mock only answers the requests going to the base URL it was given."""
    with httpx2.Client(transport=secrets.as_transport()) as client:
        with pytest.raises(HttpException, match="No registered path found"):
            client.get(f"{OTHER_URL}/secrets/some-id")


def test_base_url_can_be_left_out():
    """Without a base URL, the endpoint paths are matched wherever they are called."""
    mock = ApiMock()
    mock.add(method="GET", path="/health", handler=respond(200, json={"status": "OK"}))

    with httpx2.Client(transport=mock.as_transport()) as client:
        assert client.get(f"{BASE_URL}/health").json() == {"status": "OK"}
        assert client.get(f"{OTHER_URL}/health").json() == {"status": "OK"}


def test_added_endpoints_record_their_own_requests():
    """An endpoint registered with `add` counts the requests that reached it."""
    mock = ApiMock(base_url=BASE_URL)
    health = mock.add(method="GET", path="/health")
    ready = mock.add(method="GET", path="/ready")

    with httpx2.Client(transport=mock.as_transport()) as client:
        assert client.get(f"{BASE_URL}/health").status_code == 200
        client.get(f"{BASE_URL}/health")
        client.get(f"{BASE_URL}/ready")

    assert health.call_count == 2
    assert ready.call_count == 1
    assert len(mock.requests) == 3


def test_added_endpoint_handler_can_be_swapped():
    """The handler of an endpoint registered with `add` can be reassigned."""
    mock = ApiMock(base_url=BASE_URL)
    health = mock.add(method="GET", path="/health")

    with httpx2.Client(transport=mock.as_transport()) as client:
        assert client.get(f"{BASE_URL}/health").status_code == 200

        health.handler = respond(503)
        assert client.get(f"{BASE_URL}/health").status_code == 503


def test_several_mocks_can_share_one_router():
    """Mocks sharing a router are served by one transport, but record separately."""
    router: MockRouter = MockRouter()
    secrets = SecretsApiMock(router=router)
    boxes = BoxesApiMock(base_url=OTHER_URL, router=router)

    with httpx2.Client(transport=secrets.as_transport()) as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 200
        assert client.get(f"{OTHER_URL}/boxes/some-id").status_code == 200

    assert len(secrets.requests) == 1
    assert len(boxes.requests) == 1


@pytest.mark.asyncio
async def test_async_handlers_are_awaited(secrets: SecretsApiMock):
    """A handler may be async, which lets it answer out of something it awaits."""

    async def handler(
        request: httpx2.Request, **path_variables: str
    ) -> httpx2.Response:
        return httpx2.Response(200, json=path_variables["secret_id"])

    secrets.on_get_secret = handler

    async with httpx2.AsyncClient(transport=secrets.as_transport()) as client:
        response = await client.get(f"{BASE_URL}/secrets/some-id")

    assert response.json() == "some-id"


def test_respond_bodies():
    """`respond` tells a missing body apart from a body holding `null`."""
    request = httpx2.Request("GET", BASE_URL)

    assert respond(204)(request).content == b""  # type: ignore[union-attr]
    assert respond(200, json=None)(request).json() is None  # type: ignore[union-attr]
    assert respond(200, json={"a": 1})(request).json() == {"a": 1}  # type: ignore[union-attr]
    assert respond(200, content="text")(request).content == b"text"  # type: ignore[union-attr]


def test_fail_with():
    """`fail_with` raises the given error instead of answering."""
    error = httpx2.ReadTimeout("Simulated network problem")
    mock = ApiMock(base_url=BASE_URL)
    mock.add(method="GET", path="/health", handler=fail_with(error))

    with httpx2.Client(transport=mock.as_transport()) as client:
        with pytest.raises(httpx2.ReadTimeout, match="Simulated network problem"):
            client.get(f"{BASE_URL}/health")


def test_fail_to_connect():
    """`fail_to_connect` makes the API look unreachable."""
    mock = ApiMock(base_url=BASE_URL)
    mock.add(method="GET", path="/health", handler=fail_to_connect())

    with httpx2.Client(transport=mock.as_transport()) as client:
        with pytest.raises(httpx2.ConnectError, match="All connection attempts failed"):
            client.get(f"{BASE_URL}/health")


def test_in_sequence(secrets: SecretsApiMock):
    """`in_sequence` answers consecutive requests with one handler each."""
    secrets.on_get_secret = in_sequence(respond(202), respond(200, json="s3cret"))

    with httpx2.Client(transport=secrets.as_transport()) as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 202
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 200

        with pytest.raises(AssertionError, match="Unexpected additional request"):
            client.get(f"{BASE_URL}/secrets/some-id")


def test_unconfigured_names_the_endpoint():
    """`unconfigured` says which handler to assign to answer the call."""
    request = httpx2.Request("GET", BASE_URL)

    with pytest.raises(AssertionError, match="`on_something`"):
        unconfigured("on_something")(request)


def test_httpyexpect_body():
    """`httpyexpect_body` builds the error body a GHGA service would send."""
    assert httpyexpect_body("someError") == {
        "exception_id": "someError",
        "description": "",
        "data": {},
    }
    assert httpyexpect_body("someError", "It failed.", {"id": "1"}) == {
        "exception_id": "someError",
        "description": "It failed.",
        "data": {"id": "1"},
    }


def test_httpyexpect_error_handler():
    """A router given the handler answers unmatched calls instead of raising."""
    router: MockRouter[HttpException] = MockRouter(
        exception_handler=httpyexpect_error_handler,
        exceptions_to_handle=(HttpException,),
    )
    mock = ApiMock(base_url=BASE_URL, router=router)
    mock.add(method="GET", path="/health")

    with httpx2.Client(transport=mock.as_transport()) as client:
        response = client.get(f"{BASE_URL}/does-not-exist")

    assert response.status_code == 404
    assert response.json()["exception_id"] == "pageNotFound"
