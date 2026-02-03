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

"""Test the correlation ID middleware."""

from contextlib import nullcontext
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI, Request, Response
from hexkit.correlation import (
    CorrelationIdContextError,
    correlation_id_from_str,
    get_correlation_id,
    new_correlation_id,
    set_new_correlation_id,
)

from ghga_service_commons.api.api import (
    CORRELATION_ID_HEADER_NAME,
    ApiConfigBase,
    UnexpectedCorrelationIdError,
    configure_app,
)
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.http.correlation import (
    AsyncClient,
    attach_correlation_id_to_requests,
)

pytestmark = pytest.mark.asyncio()

VALID_CORRELATION_ID = "5deb0e61-5058-4e96-92d4-0529d045832e"


@pytest.mark.parametrize(
    "preset_id,generate_correlation_id,status_code",
    [
        (VALID_CORRELATION_ID, False, 200),  # happy path
        (VALID_CORRELATION_ID, True, 200),  # also fine
        ("invalid", False, 400),  # error for bad cid header
        ("invalid", True, 200),  # invalid ID will get replaced
        ("", False, 400),  # No error for empty string cid header
        ("", True, 200),  # empty string with generate flag is fine
    ],
)
async def test_middleware_requests(
    preset_id: str,
    generate_correlation_id: bool,
    status_code: int,
):
    """Test that the InvalidCorrelationIdErrors are returned as 400 status-code responses."""
    app = FastAPI()
    app.get("/")(lambda: "some response")

    config = ApiConfigBase(generate_correlation_id=generate_correlation_id)
    configure_app(app, config)

    async with AsyncTestClient(app=app) as rest_client:
        response = await rest_client.get(
            "/", headers={CORRELATION_ID_HEADER_NAME: preset_id}
        )

        assert response.status_code == status_code


@pytest.mark.parametrize("use_unexpected_cid", [True, False])
async def test_middleware_responses(use_unexpected_cid: bool):
    """Make sure the middleware sets the CID header on responses.

    The middleware should also raise an error if the CID value is unexpected.
    """
    app = FastAPI()

    config = ApiConfigBase()
    configure_app(app, config)

    @app.get("/")
    async def endpoint():
        if use_unexpected_cid:
            return Response(
                headers={CORRELATION_ID_HEADER_NAME: str(new_correlation_id())}
            )
        return "done"

    async with (
        set_new_correlation_id() as correlation_id,
        AsyncTestClient(app=app) as rest_client,
    ):
        # If 'use_unexpected_cid' is set, then the endpoint will return a different
        #  cid in the header. The middleware should detect this and raise an error.
        #  Our services should not have a reason to modify this value.
        cid_string = str(correlation_id)
        with (
            pytest.raises(UnexpectedCorrelationIdError)
            if use_unexpected_cid
            else nullcontext()
        ):
            response = await rest_client.get(
                "/", headers={CORRELATION_ID_HEADER_NAME: cid_string}
            )

        # Only check the response headers now if we used the normal CID
        if not use_unexpected_cid:
            assert CORRELATION_ID_HEADER_NAME in response.headers
            assert response.headers[CORRELATION_ID_HEADER_NAME] == cid_string


async def test_correlation_id_request_hook():
    """Test to see if the correlation ID is correctly propagated between services.

    Both of the defined endpoints will not raise an error when calling
    `get_correlation_id` because the default `ApiConfigBase` specifies that we
    generate and use a new correlation ID in the API middleware if one is not found in
    the ContextVar.
    """
    some_other_service = FastAPI()
    configure_app(some_other_service, ApiConfigBase())

    # Define a second/final endpoint that returns the current correlation ID
    some_other_service.get("/test")(lambda: get_correlation_id())

    this_service = FastAPI()
    configure_app(this_service, ApiConfigBase())

    @this_service.get("/")
    async def first_endpoint():
        """Call the other endpoint"""
        correlation_id = str(get_correlation_id())

        async with AsyncTestClient(app=some_other_service) as client:
            # Make a call to the other API and verify that the CID isn't passed on
            response = await client.get("/test")
            assert response.json() != correlation_id

            # Add tracing, and make sure it fails if there's not a CID already set
            attach_correlation_id_to_requests(client, generate_correlation_id=False)

            # Make another call to the other API, passing on the correlation ID
            response = await client.get("/test")
            assert response.json() == correlation_id
            assert response.headers[CORRELATION_ID_HEADER_NAME] == correlation_id
        return correlation_id

    # Kick off the request flow
    async with AsyncTestClient(app=this_service) as rest_client:
        attach_correlation_id_to_requests(rest_client, generate_correlation_id=True)
        # Verify that no CID is currently set
        with pytest.raises(CorrelationIdContextError):
            _ = get_correlation_id()

        # Verify that the CID is propagated from here to the final API endpoint and back
        async with set_new_correlation_id() as correlation_id:
            response = await rest_client.get("/")
            cid_string = str(correlation_id)
            assert response.json() == cid_string
            assert response.headers[CORRELATION_ID_HEADER_NAME] == cid_string


async def test_hook_errors():
    """Assert that we raise an error when making requests when generate_correlation_id
    is False.
    """
    app = FastAPI()

    config = ApiConfigBase()
    configure_app(app, config)

    app.get("/")(lambda: "hello world")

    async with AsyncTestClient(app=app) as client:
        attach_correlation_id_to_requests(client, generate_correlation_id=False)
        with pytest.raises(CorrelationIdContextError):
            await client.get("/")


@pytest.mark.parametrize("generate_correlation_id", [True, False])
async def test_async_client(generate_correlation_id: bool):
    """Test the custom AsyncClient class.

    It should always add the correlation ID header, and it should generate a new
    correlation ID if none exists instead of raising an error.
    """
    app = FastAPI()

    config = ApiConfigBase()
    configure_app(app, config)

    @app.get("/")
    async def endpoint(request: Request):
        """Return the correlation ID header value from the request."""
        assert CORRELATION_ID_HEADER_NAME in request.headers
        correlation_id = correlation_id_from_str(
            request.headers[CORRELATION_ID_HEADER_NAME]
        )
        return correlation_id

    # Create an AsyncClient instance (NOT AsyncTestClient!)
    async with AsyncClient(
        generate_correlation_id=generate_correlation_id,
        transport=httpx.ASGITransport(app=app),
        base_url="http://localhost:8080",
    ) as client:
        # Verify behavior outside of a CID context
        with (
            pytest.raises(CorrelationIdContextError)
            if not generate_correlation_id
            else nullcontext()
        ):
            response = await client.get("/")

        # Check the response headers, but only in the non-erring case
        if generate_correlation_id:
            assert CORRELATION_ID_HEADER_NAME in response.headers
            correlation_id = correlation_id_from_str(
                response.headers[CORRELATION_ID_HEADER_NAME]
            )

        # Verify that the CID is passed when it exists
        async with set_new_correlation_id() as correlation_id:
            cid_string = str(correlation_id)
            response = await client.get("/")
            assert response.headers[CORRELATION_ID_HEADER_NAME] == cid_string
            assert response.json() == cid_string


@pytest.mark.parametrize("generate_correlation_id", [True, False])
async def test_correlation_id_middleware_non_v4_uuid(
    generate_correlation_id: bool, caplog, monkeypatch
):
    """Test that the server middleware correctly replaces an inbound request's
    correlation ID if it isn't a valid UUID4.
    """
    app = FastAPI()

    config = ApiConfigBase(generate_correlation_id=generate_correlation_id)
    configure_app(app, config)

    @app.get("/")
    async def endpoint():
        """Return the correlation ID header value from the request."""
        return get_correlation_id()

    # Create test client and send a request with valid UUID but not a UUID4
    client = AsyncTestClient(app=app)
    non_v4_uuid = "a362ef97-f600-9b51-a5e6-163874e8778a"
    headers = {CORRELATION_ID_HEADER_NAME: non_v4_uuid}

    # Patch new_correlation_id() to produce a known value so that we can inspect the log
    caplog.clear()
    monkeypatch.setattr(
        "ghga_service_commons.api.api.new_correlation_id",
        lambda: UUID(VALID_CORRELATION_ID),
    )

    # Make a call to the endpoint defined above
    response = await client.get("/", headers=headers)

    # Test for the log generation
    if not generate_correlation_id:
        assert not caplog.records
    else:
        assert caplog.records
        assert caplog.records[0].getMessage() == (
            f"Detected a non-uuid4 value for correlation ID ({non_v4_uuid})."
            + f" Replacing with newly-generated value: {VALID_CORRELATION_ID}"
        )

    # The goal is for the middleware to catch the header and update it if
    #  generate_correlation_id is True, and otherwise return a 400 BAD REQUEST
    assert response.status_code == 200 if generate_correlation_id else 400
    if generate_correlation_id:
        raw_response = response.json()
        assert response.headers[CORRELATION_ID_HEADER_NAME] == raw_response
        assert raw_response != non_v4_uuid, "CID header was not updated by middleware"
        end_cid = UUID(raw_response)
        assert end_cid.version == 4, "CID header was updated but...somehow is not v4?"
