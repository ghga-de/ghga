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

"""REST API-focused unit tests that mock the DlqManager"""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import status
from ghga_service_commons.api.testing import AsyncTestClient

from dlqs.adapters.inbound.fastapi_ import http_exceptions as http_exc
from dlqs.inject import prepare_rest_app
from dlqs.ports.inbound.dlq_manager import DLQManagerPort
from tests.fixtures import utils
from tests.fixtures.config import DEFAULT_CONFIG

pytestmark = pytest.mark.asyncio()
TEST_UUID = UUID("f4e0fbd6-016a-488e-9051-aefaa70689e0")
TEST_UUID2 = UUID("f4e0fbd6-016a-488e-9051-aefaa70689e1")


async def test_preview_bad_params():
    """Test how ValueError is translated (from bad `skip` or `limit` args)"""
    dlq_manager = AsyncMock()
    dlq_manager.preview_events.side_effect = ValueError("bad params")
    async with (
        prepare_rest_app(
            config=DEFAULT_CONFIG,
            dlq_manager_override=dlq_manager,
        ) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.get(
            f"/{utils.UFS}/{utils.USER_EVENTS}?skip=-1&limit=0",
            headers=utils.VALID_AUTH_HEADER,
        )
        assert response.status_code == 400
        assert response.json() == {
            "description": (
                "Invalid values for `skip` and/or `limit`. Skip must be >=0 if supplied"
                + " and limit must be >=1 if supplied."
            ),
            "data": {"skip": -1, "limit": 0},
            "exception_id": "previewParamsError",
        }


@pytest.mark.parametrize(
    "internal_error, http_error, status_code",
    [
        (
            ValueError(),
            http_exc.HttpPreviewParamsError,
            400,
        ),
        (Exception("unknown error"), http_exc.HttpInternalServerError, 500),
    ],
)
async def test_preview_error_translation(
    internal_error: RuntimeError,
    http_error: type[http_exc.HttpCustomExceptionBase],
    status_code: int,
):
    """Test that domain errors are translated to HTTP error correctly"""
    dlq_manager_mock = AsyncMock()
    dlq_manager_mock.preview_events.side_effect = internal_error

    async with (
        prepare_rest_app(
            config=DEFAULT_CONFIG,
            dlq_manager_override=dlq_manager_mock,
        ) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.get(
            f"/{utils.UFS}/{utils.USER_EVENTS}", headers=utils.VALID_AUTH_HEADER
        )
        assert response.status_code == status_code
        assert response.json()["exception_id"] == http_error.exception_id


@pytest.mark.parametrize(
    "internal_error, http_error, status_code",
    [
        (
            DLQManagerPort.DLQValidationError(dlq_id=TEST_UUID, reason="bad event"),
            http_exc.HttpOverrideValidationError,
            400,
        ),
        (
            DLQManagerPort.DLQEmptyError(service="foo", topic="bar"),
            http_exc.HttpEmptyDLQError,
            404,
        ),
        (
            DLQManagerPort.DLQSequenceError(
                dlq_id=TEST_UUID, service="foo", topic="bar", next_id=TEST_UUID2
            ),
            http_exc.HttpSequenceError,
            409,
        ),
        (Exception("unknown error"), http_exc.HttpInternalServerError, 500),
    ],
)
async def test_process_error_translation(
    internal_error: RuntimeError,
    http_error: type[http_exc.HttpCustomExceptionBase],
    status_code: int,
):
    """Test that domain errors are translated to HTTP error correctly"""
    dlq_manager_mock = AsyncMock()
    dlq_manager_mock.process_event.side_effect = internal_error

    async with (
        prepare_rest_app(
            config=DEFAULT_CONFIG,
            dlq_manager_override=dlq_manager_mock,
        ) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.post(
            "/foo/bar", json={"dlq_id": str(TEST_UUID)}, headers=utils.VALID_AUTH_HEADER
        )
        assert response.status_code == status_code, str(response.json())
        assert response.json()["exception_id"] == http_error.exception_id


async def test_discard_error_translation():
    """Test that domain errors are translated to HTTP error correctly"""
    dlq_manager_mock = AsyncMock()
    dlq_manager_mock.discard_event.side_effect = RuntimeError()

    async with (
        prepare_rest_app(
            config=DEFAULT_CONFIG,
            dlq_manager_override=dlq_manager_mock,
        ) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.delete(f"/{TEST_UUID}", headers=utils.VALID_AUTH_HEADER)
        assert response.status_code == 500
        assert (
            response.json()["exception_id"]
            == http_exc.HttpInternalServerError.exception_id
        )


@pytest.mark.parametrize(
    "auth_header",
    [{}, utils.INVALID_AUTH_HEADER, {"Authorization": ""}],
    ids=["no_auth", "invalid_api_key", "empty_api_key"],
)
async def test_401_errors(auth_header: dict[str, str]):
    """Test that all endpoints other than /health return `401` if API key is absent."""
    async with (
        prepare_rest_app(
            config=DEFAULT_CONFIG,
            dlq_manager_override=AsyncMock(),
        ) as app,
        AsyncTestClient(app=app) as client,
    ):
        response = await client.get("/health", headers=auth_header)
        assert response.status_code == 200

        response = await client.get("/foo/bar", headers=auth_header)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = await client.post(
            "/foo/bar", json={"dlq_id": str(TEST_UUID)}, headers=auth_header
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        response = await client.delete(f"/{TEST_UUID}", headers=auth_header)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
