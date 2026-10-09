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
"""Tests for the HTTP API mocks in `ghga_service_commons.http.mock_api`."""

import gc
import gzip
import warnings
from collections.abc import AsyncIterator, Generator, Iterator
from typing import Any

import httpx2
import pytest

from ghga_service_commons.http.mock_api import (
    MockApi,
    MockSetupError,
    NotMockedError,
    ResponseHandler,
    fail_to_connect,
    instrumentable,
    respond,
    serve,
)

# Hosts use the `.invalid` TLD, which never resolves, so a request that escapes the mock
# fails instead of reaching a real server
TAG_URL = "http://items.invalid/api/items/i1/tags/t1"


class ItemsMock(MockApi):
    """A mock with two routes that take path variables."""

    def __init__(self, base_url: str = "http://items.invalid/api") -> None:
        super().__init__(base_url)
        self.on_get_tag: ResponseHandler = respond(200, json={"value": "x"})
        self.on_delete_item: ResponseHandler = respond(204)
        self.route("GET", "/items/{item_id}/tags/{tag}", "on_get_tag")
        self.route("DELETE", "/items/{item_id}", "on_delete_item")


class WidgetsMock(MockApi):
    """A mock whose literal route comes before a variable route matching it too."""

    def __init__(self, base_url: str = "http://widgets.invalid") -> None:
        super().__init__(base_url)
        self.on_get_latest: ResponseHandler = respond(200, json={"id": "latest"})
        self.on_get_widget: ResponseHandler = respond(200, json={"id": "any"})
        self.on_update_widget: ResponseHandler = respond(204)
        self.route("GET", "/widgets/latest", "on_get_latest")
        self.route("GET", "/widgets/{widget_id}", "on_get_widget")
        self.route("PATCH", "/widgets/{widget_id}", "on_update_widget")
        self.route("PUT", "/widgets/{widget_id}", "on_update_widget")


def test_route_answers_with_the_current_handler():
    """Test that a route answers with its handler and a test can swap it."""
    items = ItemsMock()
    client = httpx2.Client(transport=items.as_transport())

    assert client.get(TAG_URL).json() == {"value": "x"}
    items.on_get_tag = respond(404)
    assert client.get(TAG_URL).status_code == 404

    assert len(items.requests) == 2
    assert items.last_request is not None
    assert items.last_request.url == httpx2.URL(TAG_URL)


def test_query_string_does_not_affect_matching():
    """Test that a route matches the path only, and the query reaches the handler."""
    items = ItemsMock()
    client = httpx2.Client(transport=items.as_transport())

    assert client.get(TAG_URL, params={"page": "2"}).status_code == 200
    assert items.last_request is not None
    assert items.last_request.url.params["page"] == "2"


@pytest.mark.parametrize(
    "method, url",
    [
        ("GET", "http://items.invalid/api/items/i1"),  # no route for the path
        ("POST", "http://items.invalid/api/items/i1"),  # no route for the method
        ("DELETE", "http://items.invalid/api/items/i1/x"),  # a segment too many
        ("DELETE", "http://items.invalid/api/items/i1/"),  # a trailing slash
        ("DELETE", "http://items.invalid/api/items/a%2Fb"),  # an encoded slash splits
        ("DELETE", "http://items.invalid/other/items/i1"),  # outside the base path
        ("DELETE", "http://other.invalid/api/items/i1"),  # another host
        ("DELETE", "https://items.invalid/api/items/i1"),  # another scheme
    ],
)
def test_request_no_route_serves_raises(method: str, url: str):
    """Test that a request no route serves raises and is not recorded."""
    items = ItemsMock()
    client = httpx2.Client(transport=items.as_transport())

    with pytest.raises(NotMockedError):
        client.request(method, url)
    assert not items.requests


def test_routes_are_tried_in_order():
    """Test that the first route matching a request answers it."""
    widgets = WidgetsMock()
    client = httpx2.Client(transport=widgets.as_transport())

    assert client.get("http://widgets.invalid/widgets/latest").json() == {
        "id": "latest"
    }
    assert client.get("http://widgets.invalid/widgets/w1").json() == {"id": "any"}


def test_routing_to_a_missing_handler_is_refused():
    """Test that a route needs its handler set first."""

    class Incomplete(MockApi):
        def __init__(self) -> None:
            super().__init__("http://api.invalid")
            self.route("GET", "/things", "on_get_things")

    with pytest.raises(MockSetupError, match="on_get_things"):
        Incomplete()


@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", "/things/{thing-id}"),  # a hyphen in the name
        ("GET", "/things/{1thing}"),  # a name starting with a digit
        ("GET", "/things/{größe}"),  # a name that is not ASCII
        ("GET", "/things/{thing_id"),  # an unclosed variable
        ("GTE", "/things"),  # not an HTTP method
        ("GET", "/things?page=2"),  # a query, which routing ignores
    ],
)
def test_malformed_route_is_refused(method: str, path: str):
    """Test that a route that cannot match as meant is refused."""

    class Malformed(MockApi):
        def __init__(self) -> None:
            super().__init__("http://api.invalid")
            self.on_get_things: ResponseHandler = respond(200)
            self.route(method, path, "on_get_things")

    with pytest.raises(MockSetupError, match="Route"):
        Malformed()


@pytest.mark.parametrize("base_url", ["items.invalid/api", "/api"])
def test_base_url_needs_a_scheme_and_a_host(base_url: str):
    """Test that a base URL no request could ever reach is refused."""
    with pytest.raises(MockSetupError, match="scheme and a host"):
        ItemsMock(base_url)


def test_base_url_with_a_query_is_refused():
    """Test that a base URL whose query routing would ignore is refused."""
    with pytest.raises(MockSetupError, match="query"):
        ItemsMock("http://items.invalid/api?version=2")


@pytest.mark.parametrize(
    "first, second",
    [
        ("/things/{thing_id}", "things/{id}"),  # the same route again
        ("/things/{thing_id}", "/things/latest"),  # a literal route behind it
    ],
)
def test_route_an_earlier_one_answers_is_refused(first: str, second: str):
    """Test that a route an earlier one already answers is refused."""

    class Twice(MockApi):
        def __init__(self) -> None:
            super().__init__("http://api.invalid")
            self.on_get_thing: ResponseHandler = respond(200)
            self.on_read_thing: ResponseHandler = respond(200)
            self.route("GET", first, "on_get_thing")
            self.route("get", second, "on_read_thing")

    with pytest.raises(MockSetupError, match="on_get_thing"):
        Twice()


@pytest.mark.parametrize("path", ["", "/"])
def test_empty_route_path_answers_the_base_url(path: str):
    """Test that "" and "/" route the base URL, with or without its trailing slash."""

    class StatusMock(MockApi):
        def __init__(self) -> None:
            super().__init__("http://api.invalid/status")
            self.on_get_status: ResponseHandler = respond(200)
            self.route("GET", path, "on_get_status")

    client = httpx2.Client(transport=StatusMock().as_transport())

    assert client.get("http://api.invalid/status").status_code == 200
    assert client.get("http://api.invalid/status/").status_code == 200


def test_leading_slash_of_a_route_path_is_optional():
    """Test that a route path joins the base path with or without a leading slash."""

    class ThingsMock(MockApi):
        def __init__(self) -> None:
            super().__init__("http://api.invalid/v1")
            self.on_get_things: ResponseHandler = respond(200)
            self.on_get_thing: ResponseHandler = respond(200)
            self.route("GET", "things", "on_get_things")
            self.route("GET", "/things/{thing_id}", "on_get_thing")

    things = ThingsMock()
    client = httpx2.Client(transport=things.as_transport())

    assert client.get("http://api.invalid/v1/things").status_code == 200
    assert client.get("http://api.invalid/v1/things/t1").status_code == 200
    with pytest.raises(NotMockedError):
        client.get("http://api.invalid/v1things")


@pytest.mark.parametrize("path", ["/pages/a b", "/pages/a%20b"])
def test_route_path_may_be_percent_encoded(path: str):
    """Test that a route path matches whether it is written percent-encoded or not."""

    class PagesMock(MockApi):
        def __init__(self) -> None:
            super().__init__("http://api.invalid/my%20api")
            self.on_get_page: ResponseHandler = respond(200)
            self.route("GET", path, "on_get_page")

    client = httpx2.Client(transport=PagesMock().as_transport())

    assert client.get("http://api.invalid/my%20api/pages/a%20b").status_code == 200
    assert client.get("http://api.invalid/my api/pages/a b").status_code == 200


def test_last_request_without_requests_is_none():
    """Test that an untouched mock has no last request."""
    assert ItemsMock().last_request is None


@pytest.mark.asyncio
async def test_async_client_and_async_handler():
    """Test that async clients are served, and async handlers awaited."""
    items = ItemsMock()

    async def gone(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(410)

    items.on_delete_item = gone
    async with httpx2.AsyncClient(transport=items.as_transport()) as client:
        response = await client.delete("http://items.invalid/api/items/i1")
    assert response.status_code == 410


def test_async_handler_refuses_a_sync_client():
    """Test that an async handler fails a sync client's call, closing its coroutine."""
    items = ItemsMock()

    async def gone(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(410)

    items.on_delete_item = gone
    client = httpx2.Client(transport=items.as_transport())

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(MockSetupError, match="synchronous client"):
            client.delete("http://items.invalid/api/items/i1")
        gc.collect()
    assert not [
        warning for warning in caught if "never awaited" in str(warning.message)
    ]


def test_any_awaitable_answer_refuses_a_sync_client():
    """Test that an awaitable answer other than a coroutine fails a sync client too."""

    class Answer:
        def __await__(self) -> Generator[None, None, httpx2.Response]:
            yield
            return httpx2.Response(204)

    items = ItemsMock()
    items.on_delete_item = lambda request: Answer()
    client = httpx2.Client(transport=items.as_transport())

    with pytest.raises(MockSetupError, match="synchronous client"):
        client.delete("http://items.invalid/api/items/i1")


@pytest.mark.asyncio
async def test_handler_not_answering_with_a_response_is_refused():
    """Test that a handler returning no response fails, naming the request."""
    items = ItemsMock()
    url = "http://items.invalid/api/items/i1"

    def forgot_to_return(request: httpx2.Request) -> Any:
        httpx2.Response(204)

    async def forgot_to_return_async(request: httpx2.Request) -> Any:
        httpx2.Response(204)

    items.on_delete_item = forgot_to_return
    with pytest.raises(MockSetupError, match=f"DELETE {url} returned NoneType"):
        httpx2.Client(transport=items.as_transport()).delete(url)
    for handler in (forgot_to_return, forgot_to_return_async):
        items.on_delete_item = handler
        async with httpx2.AsyncClient(transport=items.as_transport()) as client:
            with pytest.raises(MockSetupError, match="returned NoneType"):
                await client.delete(url)


def test_respond():
    """Test the canned response handler."""
    request = httpx2.Request("GET", "http://api.invalid/")

    with_json = respond(201, json={"a": 1}, headers={"x-test": "1"})(request)
    assert isinstance(with_json, httpx2.Response)
    assert with_json.status_code == 201
    assert with_json.json() == {"a": 1}
    assert with_json.headers["x-test"] == "1"

    raw = respond(200, content=b"null")(request)
    assert isinstance(raw, httpx2.Response)
    assert raw.content == b"null"

    empty = respond(204)(request)
    assert isinstance(empty, httpx2.Response)
    assert empty.content == b""


def test_respond_keeps_its_answer():
    """Test that changing the body or headers given to respond() has no effect."""
    body, headers = {"state": "open"}, {"x-test": "1"}
    handler = respond(json=body, headers=headers)
    body["state"], headers["x-test"] = "closed", "2"

    response = handler(httpx2.Request("GET", "http://api.invalid/"))
    assert isinstance(response, httpx2.Response)
    assert response.json() == {"state": "open"}
    assert response.headers["x-test"] == "1"


def test_respond_refuses_two_bodies():
    """Test that respond() refuses a JSON body and content together."""
    with pytest.raises(MockSetupError, match="not both"):
        respond(200, json={"a": 1}, content=b"x")


def test_fail_to_connect():
    """Test that the failure handler raises a connection error carrying the request."""
    request = httpx2.Request("GET", "http://api.invalid/")
    with pytest.raises(httpx2.ConnectError, match="refused") as caught:
        fail_to_connect("refused")(request)
    assert caught.value.request is request


def test_serve_mocks_sharing_a_host():
    """Test that several mocks behind one transport each get their own requests."""
    items = ItemsMock("http://apis.invalid/first")
    widgets = WidgetsMock("http://apis.invalid/second")
    client = httpx2.Client(transport=serve(items, widgets))

    assert client.get("http://apis.invalid/second/widgets/w1").status_code == 200
    assert client.get("http://apis.invalid/first/items/i1/tags/t1").status_code == 200
    assert (len(items.requests), len(widgets.requests)) == (1, 1)

    with pytest.raises(NotMockedError, match="No mock serves"):
        client.get("http://apis.invalid/other")


@pytest.mark.asyncio
async def test_instrumentable_transport_answers_async_clients():
    """Test that the instrumentable transport answers like the mock transport."""
    items = ItemsMock()

    async def body() -> AsyncIterator[bytes]:
        yield b"chunk"

    items.on_delete_item = fail_to_connect()
    transport = instrumentable(items.as_transport())
    async with httpx2.AsyncClient(transport=transport) as client:
        response = await client.get(TAG_URL, params={"page": "2"})
        assert response.json() == {"value": "x"}
        with pytest.raises(httpx2.ConnectError):
            await client.request(
                "DELETE", "http://items.invalid/api/items/i1", content=body()
            )
    assert items.requests[0].url.params["page"] == "2"
    assert "timeout" in items.requests[0].extensions
    assert items.last_request is not None
    assert items.last_request.content == b"chunk"


@pytest.mark.asyncio
async def test_instrumentable_transport_passes_a_compressed_body_on():
    """Test that a compressed body reaches the client still compressed."""
    items = ItemsMock()
    items.on_get_tag = respond(
        200,
        content=gzip.compress(b'{"value": "x"}'),
        headers={"content-encoding": "gzip"},
    )

    transport = instrumentable(items.as_transport())
    async with httpx2.AsyncClient(transport=transport) as client:
        response = await client.get(TAG_URL)
    assert response.json() == {"value": "x"}


@pytest.fixture
def span_exporter() -> Iterator[Any]:
    """Instrument httpx2 globally for one test, collecting its spans in memory."""
    httpx_instrumentation = pytest.importorskip("opentelemetry.instrumentation.httpx")
    trace_sdk = pytest.importorskip("opentelemetry.sdk.trace")
    export = pytest.importorskip("opentelemetry.sdk.trace.export")
    in_memory = pytest.importorskip(
        "opentelemetry.sdk.trace.export.in_memory_span_exporter"
    )
    exporter = in_memory.InMemorySpanExporter()
    provider = trace_sdk.TracerProvider()
    provider.add_span_processor(export.SimpleSpanProcessor(exporter))
    instrumentor = httpx_instrumentation.HTTPX2ClientInstrumentor()
    instrumentor.instrument(tracer_provider=provider)
    try:
        yield exporter
    finally:
        instrumentor.uninstrument()


@pytest.mark.asyncio
async def test_only_the_instrumentable_transport_records_client_spans(
    span_exporter: Any,
):
    """Test that global instrumentation sees the opt-in transport, not the mock one."""
    items = ItemsMock()
    async with httpx2.AsyncClient(transport=items.as_transport()) as client:
        await client.get(TAG_URL)
    assert span_exporter.get_finished_spans() == ()

    transport = instrumentable(items.as_transport())
    async with httpx2.AsyncClient(transport=transport) as client:
        await client.get(TAG_URL)
    spans = span_exporter.get_finished_spans()
    assert [span.name for span in spans] == ["GET"]
    assert spans[0].kind.name == "CLIENT"
    assert len(items.requests) == 2
