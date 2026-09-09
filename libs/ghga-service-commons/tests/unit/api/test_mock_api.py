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

"""Tests for the API mocks."""

import gc
import warnings
from typing import Any
from uuid import UUID

import httpx2
import pytest

from ghga_service_commons.api.mock_api import (
    MockedApi,
    MockedApis,
    MockSetupError,
    NetworkPolicy,
    NotMockedError,
    ResponseHandler,
    any_network,
    endpoint,
    fail_to_connect,
    fail_with,
    httpyexpect_body,
    in_sequence,
    local_network,
    network_at,
    no_network,
    respond,
)
from ghga_service_commons.httpyexpect.server.exceptions import HttpException

BASE_URL = "http://secrets.test/api"
OTHER_URL = "http://boxes.test"


class MockedSecretsApi(MockedApi):
    """A mock of a small API, as a service would model the ones it calls."""

    base_url = BASE_URL

    on_get_secret = endpoint("GET", "/secrets/{secret_id}", respond(200, json="s3cret"))
    on_delete_secret = endpoint("DELETE", "/secrets/{secret_id}", respond(204))
    on_deposit_secret = endpoint("POST", "/secrets")


class MockedBoxesApi(MockedApi):
    """A mock of a second API, to test routing between them."""

    base_url = OTHER_URL

    on_get_box = endpoint("GET", "/boxes/{box_id}", respond(200, json={"id": "box"}))


@pytest.fixture(name="secrets")
def secrets_fixture() -> MockedSecretsApi:
    """Get a mock of the secrets API."""
    return MockedSecretsApi()


async def an_async_handler(
    request: httpx2.Request, **path_variables: str
) -> httpx2.Response:
    """Answer from something the caller has to await."""
    return httpx2.Response(200, json="from async")


class MockedAsyncApi(MockedApi):
    """A mock whose endpoint is answered by an async handler."""

    base_url = BASE_URL

    on_get = endpoint("GET", "/x", an_async_handler)


def test_endpoints_answer_with_their_defaults(secrets: MockedSecretsApi):
    """An endpoint that a test says nothing about answers with its default."""
    with MockedApis(secrets), httpx2.Client() as client:
        response = client.get(f"{BASE_URL}/secrets/some-id")
        assert response.status_code == 200
        assert response.json() == "s3cret"
        assert client.delete(f"{BASE_URL}/secrets/some-id").status_code == 204


def test_assigned_handler_takes_over(secrets: MockedSecretsApi):
    """Assigning a handler changes how the endpoint answers the calls that follow."""
    with MockedApis(secrets), httpx2.Client() as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 200

        secrets.on_get_secret = respond(500)
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 500


def test_handlers_do_not_leak_between_instances(secrets: MockedSecretsApi):
    """A handler assigned to one mock does not leak into the next one."""
    secrets.on_get_secret = respond(500)

    with MockedApis(MockedSecretsApi()), httpx2.Client() as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 200


def test_endpoint_without_default_refuses(secrets: MockedSecretsApi):
    """An endpoint declared without a default does not make up a response."""
    with MockedApis(secrets), httpx2.Client() as client:
        with pytest.raises(MockSetupError, match="`on_deposit_secret`"):
            client.post(f"{BASE_URL}/secrets", json={})

        secrets.on_deposit_secret = respond(201, json={"secret_id": "some-id"})
        assert client.post(f"{BASE_URL}/secrets", json={}).status_code == 201


def test_an_endpoint_can_be_redeclared_by_a_subclass():
    """A subclass declaring the same attribute replaces the parent's endpoint."""

    class MockedQuieterSecretsApi(MockedSecretsApi):
        on_get_secret = endpoint("GET", "/secrets/{secret_id}", respond(404))

    with MockedApis(MockedQuieterSecretsApi()), httpx2.Client() as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 404


def test_a_mock_needs_a_base_url():
    """A mock that does not say which API it serves is refused."""
    with pytest.raises(MockSetupError, match="needs the base URL"):
        MockedApi()


def test_a_base_url_needs_a_scheme_and_a_host():
    """A base URL that cannot address an API is refused where it is given."""
    with pytest.raises(MockSetupError, match="needs a scheme and a host"):
        MockedApi("secrets.test/api")


def test_an_endpoint_path_gets_a_leading_slash():
    """A path without one is served as though it had it, not run into the base URL."""

    class MockedSlashlessApi(MockedApi):
        base_url = OTHER_URL
        on_get = endpoint("GET", "secrets/{secret_id}", respond(200))

    assert MockedSlashlessApi.on_get.path == "/secrets/{secret_id}"

    with MockedApis(MockedSlashlessApi()), httpx2.Client() as client:
        assert client.get(f"{OTHER_URL}/secrets/some-id").status_code == 200


def test_every_http_method_can_be_declared():
    """`HEAD` and `OPTIONS` are served like any other method."""

    class MockedThingApi(MockedApi):
        base_url = OTHER_URL
        on_head = endpoint("HEAD", "/x", respond(200))
        on_options = endpoint("OPTIONS", "/x", respond(204))

    with MockedApis(MockedThingApi()), httpx2.Client() as client:
        assert client.head(f"{OTHER_URL}/x").status_code == 200
        assert client.request("OPTIONS", f"{OTHER_URL}/x").status_code == 204


def test_an_endpoint_needs_an_http_method():
    """A method that is not one is refused where it is declared."""
    with pytest.raises(MockSetupError, match="not an HTTP method"):
        endpoint("FETCH", "/secrets")


def test_path_variables_reach_the_handler(secrets: MockedSecretsApi):
    """The `{variables}` in the path arrive as keyword arguments."""
    seen: dict[str, str] = {}

    def handler(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        seen.update(path_variables)
        return httpx2.Response(200)

    secrets.on_get_secret = handler
    with MockedApis(secrets), httpx2.Client() as client:
        client.get(f"{BASE_URL}/secrets/some-id")

    assert seen == {"secret_id": "some-id"}


def test_endpoint_paths_are_matched_literally():
    """A `.` in a path matches a `.`, not any character."""

    class MockedFilesApi(MockedApi):
        base_url = BASE_URL
        on_get_file = endpoint("GET", "/files/{file_id}.json", respond(200))

    with MockedApis(MockedFilesApi()), httpx2.Client() as client:
        assert client.get(f"{BASE_URL}/files/abc.json").status_code == 200

    with pytest.raises(NotMockedError):
        with MockedApis(MockedFilesApi()), httpx2.Client() as client:
            client.get(f"{BASE_URL}/files/abcXjson")


def test_query_string_does_not_hide_the_endpoint(secrets: MockedSecretsApi):
    """An endpoint serves its path whether the call carries query parameters or not."""
    with MockedApis(secrets), httpx2.Client() as client:
        assert client.get(f"{BASE_URL}/secrets/x?verbose=true").status_code == 200


def test_a_call_no_endpoint_serves_is_refused(secrets: MockedSecretsApi):
    """A request the mock was meant to answer but has no endpoint for is refused."""
    with pytest.raises(NotMockedError, match="none of its endpoints serve"):
        with MockedApis(secrets), httpx2.Client() as client:
            client.get(f"{BASE_URL}/other-thing")


def test_a_method_no_endpoint_is_declared_under_is_refused(secrets: MockedSecretsApi):
    """A path served under one method does not answer another."""
    with pytest.raises(NotMockedError):
        with MockedApis(secrets), httpx2.Client() as client:
            client.put(f"{BASE_URL}/secrets/some-id")


def test_requests_are_recorded(secrets: MockedSecretsApi):
    """Every request that reaches the mock is recorded, in order."""
    with MockedApis(secrets), httpx2.Client() as client:
        client.get(f"{BASE_URL}/secrets/first")
        client.get(f"{BASE_URL}/secrets/second")

    assert len(secrets.requests) == 2
    assert secrets.last_request is not None
    assert str(secrets.last_request.url) == f"{BASE_URL}/secrets/second"


def test_requests_are_recorded_per_endpoint(secrets: MockedSecretsApi):
    """`calls` says which endpoint answered what, keyed by the attribute name."""
    with MockedApis(secrets), httpx2.Client() as client:
        client.get(f"{BASE_URL}/secrets/first")
        client.delete(f"{BASE_URL}/secrets/second")

    assert len(secrets.calls["on_get_secret"]) == 1
    assert (
        str(secrets.calls["on_delete_secret"][-1].url) == f"{BASE_URL}/secrets/second"
    )
    assert secrets.calls["on_deposit_secret"] == []


def test_last_request_without_any_request(secrets: MockedSecretsApi):
    """Asking for the last request before there is one says there is none."""
    assert secrets.last_request is None


def test_reset_forgets_the_requests_and_puts_the_defaults_back(
    secrets: MockedSecretsApi,
):
    """A reset mock is indistinguishable from a fresh one."""
    with MockedApis(secrets) as apis, httpx2.Client() as client:
        secrets.on_get_secret = respond(500)
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 500

        apis.reset()
        assert secrets.requests == []
        assert secrets.calls["on_get_secret"] == []
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 200


def answered(handler: ResponseHandler) -> httpx2.Response:
    """Call a handler that is not async, for a test asserting on what it answers."""
    response = handler(httpx2.Request("GET", BASE_URL))
    assert isinstance(response, httpx2.Response)
    return response


def test_respond_bodies():
    """`respond` tells a JSON `null` apart from no body at all."""
    assert answered(respond(204)).content == b""
    assert answered(respond(200, json=None)).json() is None
    assert answered(respond(200, json={"a": 1})).json() == {"a": 1}
    assert answered(respond(200, content="text")).text == "text"
    assert (
        answered(respond(200, json=1, headers={"x-test": "1"})).headers["x-test"] == "1"
    )


def test_fail_with(secrets: MockedSecretsApi):
    """A handler can raise instead of answering."""
    secrets.on_get_secret = fail_with(httpx2.ReadTimeout("too slow"))

    with MockedApis(secrets), httpx2.Client() as client:
        with pytest.raises(httpx2.ReadTimeout):
            client.get(f"{BASE_URL}/secrets/some-id")


def test_fail_to_connect(secrets: MockedSecretsApi):
    """A handler can make the API look unreachable."""
    secrets.on_get_secret = fail_to_connect()

    with MockedApis(secrets), httpx2.Client() as client:
        with pytest.raises(httpx2.ConnectError):
            client.get(f"{BASE_URL}/secrets/some-id")


def test_in_sequence(secrets: MockedSecretsApi):
    """Consecutive requests can be answered one handler at a time."""
    secrets.on_get_secret = in_sequence(respond(500), respond(200, json="s3cret"))

    with MockedApis(secrets), httpx2.Client() as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 500
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 200
        with pytest.raises(MockSetupError, match="Unexpected additional request"):
            client.get(f"{BASE_URL}/secrets/some-id")


def test_a_stateful_default_does_not_leak_into_the_next_test():
    """A declared `in_sequence` default starts over for every mock."""

    class MockedSequencedApi(MockedApi):
        base_url = BASE_URL
        on_get = endpoint("GET", "/x", in_sequence(respond(418)))

    for _ in range(2):
        with MockedApis(MockedSequencedApi()), httpx2.Client() as client:
            assert client.get(f"{BASE_URL}/x").status_code == 418


def test_httpyexpect_body():
    """The httpyexpect body has the three keys the clients look for."""
    assert httpyexpect_body("someError") == {
        "exception_id": "someError",
        "description": "",
        "data": {},
    }


def test_a_handler_raising_httpexception_becomes_a_response(secrets: MockedSecretsApi):
    """Raising `HttpException` is how a mock reports the API's own errors."""
    secrets.on_get_secret = fail_with(
        HttpException(
            status_code=404,
            exception_id="secretNotFound",
            description="no such secret",
            data={},
        )
    )

    with MockedApis(secrets), httpx2.Client() as client:
        response = client.get(f"{BASE_URL}/secrets/some-id")

    assert response.status_code == 404
    assert response.json() == httpyexpect_body("secretNotFound", "no such secret")


@pytest.mark.asyncio
async def test_an_async_handler_raising_httpexception_becomes_a_response():
    """What an async handler raises is converted the same way."""

    async def handler(
        request: httpx2.Request, **path_variables: str
    ) -> httpx2.Response:
        raise HttpException(
            status_code=418, exception_id="teapot", description="", data={}
        )

    mock = MockedAsyncApi()
    mock.on_get = handler

    with MockedApis(mock):
        async with httpx2.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/x")

    assert response.status_code == 418
    assert response.json()["exception_id"] == "teapot"


@pytest.mark.asyncio
async def test_an_async_handler_serves_an_async_client():
    """An async handler answers a caller that can wait for it."""
    with MockedApis(MockedAsyncApi()):
        async with httpx2.AsyncClient() as client:
            assert (await client.get(f"{BASE_URL}/x")).json() == "from async"


def test_an_async_handler_on_a_sync_client_says_so():
    """A synchronous client cannot wait for an async handler, and is told why."""
    with MockedApis(MockedAsyncApi()), httpx2.Client() as client:
        with pytest.raises(MockSetupError, match="is async, but the call was made"):
            client.get(f"{BASE_URL}/x")


def test_an_async_handler_on_a_sync_client_leaves_no_stray_coroutine():
    """The refused handler's coroutine is closed rather than raising a RuntimeWarning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        with MockedApis(MockedAsyncApi()), httpx2.Client() as client:
            with pytest.raises(MockSetupError, match="is async, but the call was made"):
                client.get(f"{BASE_URL}/x")
        gc.collect()


@pytest.mark.asyncio
async def test_both_kinds_of_client_are_served(secrets: MockedSecretsApi):
    """The two paths answer from the same mocks."""
    with MockedApis(secrets):
        with httpx2.Client() as client:
            assert client.get(f"{BASE_URL}/secrets/one").status_code == 200
        async with httpx2.AsyncClient() as client:
            assert (await client.get(f"{BASE_URL}/secrets/two")).status_code == 200

    assert len(secrets.requests) == 2


def test_one_set_serves_several_apis(secrets: MockedSecretsApi):
    """Each API answers its own calls, whatever order the mocks were passed in."""
    boxes = MockedBoxesApi()

    with MockedApis(boxes, secrets), httpx2.Client() as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").json() == "s3cret"
        assert client.get(f"{OTHER_URL}/boxes/some-id").json() == {"id": "box"}

    assert len(secrets.requests) == 1
    assert len(boxes.requests) == 1


def test_a_nested_api_gets_its_own_calls():
    """The API with the longer base URL answers what falls under it."""

    class MockedOuterApi(MockedApi):
        base_url = "http://host.test/api"
        on_get = endpoint("GET", "/thing", respond(200, json="outer"))

    class MockedInnerApi(MockedApi):
        base_url = "http://host.test/api/v2"
        on_get = endpoint("GET", "/thing", respond(200, json="inner"))

    with MockedApis(MockedOuterApi(), MockedInnerApi()), httpx2.Client() as client:
        assert client.get("http://host.test/api/thing").json() == "outer"
        assert client.get("http://host.test/api/v2/thing").json() == "inner"


def test_two_mocks_on_one_base_url_are_refused(secrets: MockedSecretsApi):
    """Two mocks claiming the same API would leave one of them unreachable."""
    with pytest.raises(MockSetupError, match="both serve"):
        MockedApis(secrets, MockedSecretsApi())


def test_a_url_under_another_host_is_not_claimed(secrets: MockedSecretsApi):
    """A base URL claims its own host only."""
    with pytest.raises(NotMockedError, match="tried to reach"):
        with MockedApis(secrets), httpx2.Client() as client:
            client.get("http://elsewhere.test/api/secrets/some-id")


def test_a_set_matches_on_url_boundaries():
    """A base URL does not claim another one that merely starts the same way."""
    with pytest.raises(NotMockedError, match="tried to reach"):
        with MockedApis(MockedSecretsApi()), httpx2.Client() as client:
            client.get("http://secrets.test/api-v2/secrets/some-id")


def test_a_base_url_is_matched_past_its_loopback_spelling():
    """A mock registered on one spelling of loopback answers the others."""
    mock = MockedSecretsApi("http://localhost:8080/api")

    with MockedApis(mock), httpx2.Client() as client:
        assert (
            client.get("http://127.0.0.1:8080/api/secrets/some-id").status_code == 200
        )


def test_an_unmocked_url_is_refused_by_default(secrets: MockedSecretsApi):
    """Traffic bound for the internet does not quietly go out."""
    with pytest.raises(NotMockedError, match="tried to reach"):
        with MockedApis(secrets), httpx2.Client() as client:
            client.get("https://example.org/")


@pytest.mark.parametrize(
    "url, expected",
    [
        ("http://localhost:8080/", True),
        ("http://127.0.0.1:8080/", True),
        ("http://host.docker.internal:8080/", True),
        ("http://172.17.0.2:8080/", True),
        ("https://example.org/", False),
    ],
)
def test_local_network_lets_out_what_the_test_environment_runs(
    url: str, expected: bool
):
    """Testcontainers is reachable under whatever address Docker reports."""
    assert local_network(httpx2.URL(url)) is expected


def test_the_network_policy_decides_what_goes_out(secrets: MockedSecretsApi):
    """`allow_network` decides what a request no mock serves may still do."""
    reached: list[str] = []

    def record(transport, request: httpx2.Request) -> httpx2.Response:
        reached.append(str(request.url))
        return httpx2.Response(200)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(httpx2.HTTPTransport, "handle_request", record)
        with MockedApis(secrets, allow_network=any_network), httpx2.Client() as client:
            assert client.get("https://example.org/").status_code == 200
        assert reached == ["https://example.org/"]


def test_no_network_refuses_even_loopback(secrets: MockedSecretsApi):
    """The strictest policy insists that every call is served by a mock."""
    with pytest.raises(NotMockedError):
        with MockedApis(secrets, allow_network=no_network), httpx2.Client() as client:
            client.get("http://localhost:8080/")


def test_network_at_lets_out_the_named_hosts_only():
    """A policy can name exactly what the test environment runs."""
    policy = network_at("storage.test")
    assert policy(httpx2.URL("http://storage.test/bucket")) is True
    assert policy(httpx2.URL("http://elsewhere.test/")) is False


def test_a_client_the_test_never_sees_is_served(secrets: MockedSecretsApi):
    """A client built by the code under test is answered from the mocks too."""
    with MockedApis(secrets):
        assert httpx2.get(f"{BASE_URL}/secrets/some-id").json() == "s3cret"

    assert len(secrets.requests) == 1


def test_a_stacked_transport_still_bottoms_out_in_the_mocks(secrets: MockedSecretsApi):
    """Whatever a client stacks on top, it reaches the network through the patched transport."""

    class Wrapping(httpx2.BaseTransport):
        def __init__(self) -> None:
            self.inner = httpx2.HTTPTransport()

        def handle_request(self, request: httpx2.Request) -> httpx2.Response:
            return self.inner.handle_request(request)

    with MockedApis(secrets), httpx2.Client(transport=Wrapping()) as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").json() == "s3cret"


def test_uninstalling_puts_httpx_back(secrets: MockedSecretsApi):
    """What was patched is put back on the way out, even when the test fails."""
    before = (
        httpx2.HTTPTransport.handle_request,
        httpx2.AsyncHTTPTransport.handle_async_request,
    )
    with pytest.raises(RuntimeError):
        with MockedApis(secrets):
            raise RuntimeError("the test failed")

    assert (
        httpx2.HTTPTransport.handle_request,
        httpx2.AsyncHTTPTransport.handle_async_request,
    ) == before


def test_installing_the_same_set_twice_is_refused(secrets: MockedSecretsApi):
    """A set that is already installed says so rather than losing what it replaced."""
    with MockedApis(secrets) as apis:
        with pytest.raises(MockSetupError, match="already installed"):
            apis.install()


def test_nested_sets_come_off_in_order(secrets: MockedSecretsApi):
    """The inner set answers first, and both put back what they found."""
    before = httpx2.HTTPTransport.handle_request
    boxes = MockedBoxesApi()

    with MockedApis(secrets), MockedApis(boxes), httpx2.Client() as client:
        assert client.get(f"{OTHER_URL}/boxes/some-id").status_code == 200
        with pytest.raises(NotMockedError):
            client.get(f"{BASE_URL}/secrets/some-id")

    assert httpx2.HTTPTransport.handle_request is before


def test_taking_sets_off_out_of_order_is_refused(secrets: MockedSecretsApi):
    """Restoring the outer set's patching from the inner one would outlive both."""
    outer = MockedApis(secrets)
    inner = MockedApis(MockedBoxesApi())
    outer.install()
    inner.install()
    try:
        with pytest.raises(MockSetupError, match="in the order they were installed"):
            outer.uninstall()
    finally:
        inner.uninstall()
        outer.uninstall()


def test_check_for_complaints_reports_a_call_no_endpoint_served(
    secrets: MockedSecretsApi,
):
    """A refusal the code under test swallowed still surfaces to whoever asks."""

    def swallow(request: httpx2.Request, **path_variables: str) -> httpx2.Response:
        with httpx2.Client() as client:
            try:
                client.get(f"{BASE_URL}/other-thing")
            except NotMockedError:
                pass
        return httpx2.Response(200)

    secrets.on_get_secret = swallow
    with MockedApis(secrets) as apis, httpx2.Client() as client:
        client.get(f"{BASE_URL}/secrets/some-id")

    assert any(
        "none of its endpoints serve" in complaint
        for complaint in apis.check_for_complaints()
    )


def test_check_for_complaints_reports_an_endpoint_nothing_called(
    secrets: MockedSecretsApi,
):
    """A handler set up and never used is reported, and leaving the block is not enough.

    `raise_for_complaints` is how a test opts into failing on the same report.
    """
    with MockedApis(secrets) as apis:
        secrets.on_get_secret = respond(500)

    assert any(
        "nothing called" in complaint for complaint in apis.check_for_complaints()
    )
    with pytest.raises(MockSetupError, match="nothing called"):
        apis.raise_for_complaints()


def test_a_handler_set_up_after_the_endpoint_answered_is_still_reported(
    secrets: MockedSecretsApi,
):
    """An earlier call does not cover for a handler set up afterwards."""
    with MockedApis(secrets) as apis, httpx2.Client() as client:
        client.get(f"{BASE_URL}/secrets/some-id")
        secrets.on_get_secret = respond(500)

    assert any(
        "nothing called" in complaint for complaint in apis.check_for_complaints()
    )


def test_an_endpoint_can_be_declared_as_a_decorator():
    """An endpoint can be written over the body that answers it by default."""

    class MockedDecoratedApi(MockedApi):
        base_url = BASE_URL

        @endpoint("GET", "/secrets/{secret_id}")
        def on_get_secret(
            self, request: httpx2.Request, **path_variables: str
        ) -> httpx2.Response:
            return httpx2.Response(200, json=path_variables["secret_id"])

    assert MockedDecoratedApi.on_get_secret.path == "/secrets/{secret_id}"

    with MockedApis(MockedDecoratedApi()), httpx2.Client() as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").json() == "some-id"


def test_a_decorated_endpoint_is_still_overridden_by_the_test():
    """The decorated body is a default like any other, not a fixed answer."""

    class MockedDecoratedApi(MockedApi):
        base_url = BASE_URL

        @endpoint("GET", "/secrets/{secret_id}")
        def on_get_secret(
            self, request: httpx2.Request, **path_variables: str
        ) -> httpx2.Response:
            return httpx2.Response(200)

    mock = MockedDecoratedApi()
    mock.on_get_secret = respond(500)

    with MockedApis(mock), httpx2.Client() as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").status_code == 500


def test_path_variables_are_cast_to_the_types_the_handler_declares(
    secrets: MockedSecretsApi,
):
    """A handler naming a path variable gets it as the type it annotated."""
    seen: dict[str, Any] = {}

    def handler(request: httpx2.Request, *, secret_id: UUID) -> httpx2.Response:
        seen["secret_id"] = secret_id
        return httpx2.Response(200)

    secrets.on_get_secret = handler
    secret_id = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"

    with MockedApis(secrets), httpx2.Client() as client:
        assert client.get(f"{BASE_URL}/secrets/{secret_id}").status_code == 200

    assert seen == {"secret_id": UUID(secret_id)}


def test_an_unannotated_path_variable_stays_a_string(secrets: MockedSecretsApi):
    """Only an annotation asks for a cast; without one the URL's text comes through."""
    seen: dict[str, Any] = {}

    def handler(request: httpx2.Request, *, secret_id) -> httpx2.Response:
        seen["secret_id"] = secret_id
        return httpx2.Response(200)

    secrets.on_get_secret = handler
    with MockedApis(secrets), httpx2.Client() as client:
        client.get(f"{BASE_URL}/secrets/12345")

    assert seen == {"secret_id": "12345"}


def test_a_value_that_will_not_cast_is_the_api_answering(secrets: MockedSecretsApi):
    """A URL the API cannot read is a 422, not a broken test."""

    def handler(request: httpx2.Request, *, secret_id: int) -> httpx2.Response:
        return httpx2.Response(200)

    secrets.on_get_secret = handler
    with MockedApis(secrets), httpx2.Client() as client:
        response = client.get(f"{BASE_URL}/secrets/not-a-number")

    assert response.status_code == 422
    assert response.json()["exception_id"] == "malformedUrl"


def test_a_handler_that_cannot_take_a_path_variable_is_refused(
    secrets: MockedSecretsApi,
):
    """A handler with nowhere to put a declared variable is the test set up wrong."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200)

    secrets.on_get_secret = handler
    with pytest.raises(MockSetupError, match="takes no 'secret_id'"):
        with MockedApis(secrets), httpx2.Client() as client:
            client.get(f"{BASE_URL}/secrets/some-id")


def test_as_transport_serves_the_client_it_is_mounted_on(secrets: MockedSecretsApi):
    """Code that takes a transport is served without patching anything globally."""
    apis = MockedApis(secrets)
    untouched = httpx2.HTTPTransport.handle_request

    with httpx2.Client(transport=apis.as_transport()) as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").json() == "s3cret"

    assert len(secrets.requests) == 1
    assert httpx2.HTTPTransport.handle_request is untouched


@pytest.mark.asyncio
async def test_as_transport_serves_an_async_client(secrets: MockedSecretsApi):
    """The same transport answers a caller that awaits it."""
    apis = MockedApis(secrets)

    async with httpx2.AsyncClient(transport=apis.as_transport()) as client:
        assert (await client.get(f"{BASE_URL}/secrets/some-id")).json() == "s3cret"


def test_as_transport_hands_what_no_mock_serves_to_the_inner_transport(
    secrets: MockedSecretsApi,
):
    """A permitted request goes on to the transport underneath, so stacking works."""
    seen: list[httpx2.URL] = []

    class Recording(httpx2.BaseTransport):
        def handle_request(self, request: httpx2.Request) -> httpx2.Response:
            seen.append(request.url)
            return httpx2.Response(200, json="from the inner transport")

    apis = MockedApis(secrets, allow_network=any_network)
    with httpx2.Client(transport=apis.as_transport(Recording())) as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").json() == "s3cret"
        assert client.get("http://elsewhere.test/thing").json() == (
            "from the inner transport"
        )

    assert seen == [httpx2.URL("http://elsewhere.test/thing")]


@pytest.mark.parametrize(
    "allow_network, error, message",
    [
        (any_network, MockSetupError, "nothing to send it with"),
        (no_network, NotMockedError, "tried to reach"),
    ],
)
def test_as_transport_refuses_what_it_will_not_send(
    secrets: MockedSecretsApi,
    allow_network: NetworkPolicy,
    error: type[Exception],
    message: str,
):
    """A request no mock serves stops here, whether it is let out or not."""
    apis = MockedApis(secrets, allow_network=allow_network)

    with httpx2.Client(transport=apis.as_transport()) as client:
        with pytest.raises(error, match=message):
            client.get("http://elsewhere.test/thing")


def test_a_mock_serves_itself_through_a_transport(secrets: MockedSecretsApi):
    """One mock is the common case, and it need not be wrapped by hand to be served."""
    with httpx2.Client(transport=secrets.as_transport()) as client:
        assert client.get(f"{BASE_URL}/secrets/some-id").json() == "s3cret"
        with pytest.raises(NotMockedError, match="tried to reach"):
            client.get("http://elsewhere.test/thing")  # nothing let out by default


def test_a_default_declared_as_a_method_answers_from_the_mock_state():
    """A stateful mock can answer out of its own attributes, not by swapping handlers."""

    class MockedStatefulApi(MockedApi):
        base_url = BASE_URL

        @endpoint("GET", "/things/{thing_id}")
        def on_get_thing(
            self, request: httpx2.Request, *, thing_id: str
        ) -> httpx2.Response:
            return httpx2.Response(self.status_code, json={"id": thing_id})

        def __init__(self, base_url: str = "") -> None:
            super().__init__(base_url)
            self.status_code = 200

    with MockedApis(MockedStatefulApi()), httpx2.Client() as client:
        assert client.get(f"{BASE_URL}/things/abc").json() == {"id": "abc"}

    unhappy = MockedStatefulApi()
    unhappy.status_code = 503
    with MockedApis(unhappy), httpx2.Client() as client:
        assert client.get(f"{BASE_URL}/things/abc").status_code == 503


def test_a_method_default_is_not_a_handler_the_test_set_up():
    """A mock answering from its own state need not be exercised by every test."""

    class MockedStatefulApi(MockedApi):
        base_url = BASE_URL

        @endpoint("GET", "/things")
        def on_get_things(self, request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(200)

    with MockedApis(MockedStatefulApi()) as apis:
        pass

    assert (
        apis.check_for_complaints() == []
    )  # a default is not a handler the test set up


def test_as_transport_closes_the_transport_underneath(secrets: MockedSecretsApi):
    """The transport it was handed to send with is its to close."""
    closed: list[str] = []

    class Closing(httpx2.BaseTransport):
        def handle_request(self, request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(200)

        def close(self) -> None:
            closed.append("closed")

    apis = MockedApis(secrets, allow_network=any_network)
    with httpx2.Client(transport=apis.as_transport(Closing())) as client:
        client.get(f"{BASE_URL}/secrets/some-id")

    assert closed == ["closed"]


@pytest.mark.asyncio
async def test_as_transport_closes_the_async_transport_underneath(
    secrets: MockedSecretsApi,
):
    """The same, for the transport an asynchronous client closes."""
    closed: list[str] = []

    class Closing(httpx2.AsyncBaseTransport):
        async def handle_async_request(
            self, request: httpx2.Request
        ) -> httpx2.Response:
            return httpx2.Response(200)

        async def aclose(self) -> None:
            closed.append("closed")

    apis = MockedApis(secrets, allow_network=any_network)
    async with httpx2.AsyncClient(transport=apis.as_transport(Closing())) as client:
        await client.get(f"{BASE_URL}/secrets/some-id")

    assert closed == ["closed"]
