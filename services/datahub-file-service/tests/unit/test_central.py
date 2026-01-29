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

"""Unit tests for the S3 interrogation bucket cleanup logic"""

import base64
import json
import os
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import Literal, cast
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from ghga_service_commons.auth.jwt_auth import JWTAuthConfig, JWTAuthContextProvider
from ghga_service_commons.utils.crypt import decrypt
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.utils import now_utc_ms_prec
from pydantic import BaseModel, SecretBytes
from pytest_httpx import HTTPXMock

from dhfs.adapters.outbound.central import CentralClient
from dhfs.adapters.outbound.http import get_configured_httpx_client
from dhfs.config import Config
from dhfs.models import InterrogationReport
from tests.fixtures.utils import CENTRAL_CRYPT4GH_PRIVATE_KEY, DHFS_JWK

pytestmark = pytest.mark.asyncio()


def make_interrogation_success_report(storage_alias: str) -> InterrogationReport:
    """Creates a successful InterrogationReport with the requested storage alias value"""
    return InterrogationReport(
        file_id=uuid4(),
        storage_alias=storage_alias,
        interrogated_at=now_utc_ms_prec(),
        passed=True,
        secret=SecretBytes(os.urandom(32)),
        encrypted_parts_md5=["abc123", "def456", "ghi789"],
        encrypted_parts_sha256=["123abc", "456def", "789ghi"],
    )


def make_interrogation_failure_report(storage_alias: str) -> InterrogationReport:
    """Creates a failed InterrogationReport with the requested storage alias value"""
    return InterrogationReport(
        file_id=uuid4(),
        storage_alias=storage_alias,
        interrogated_at=now_utc_ms_prec(),
        passed=False,
        reason="SHA-256 checksum over decrypted content did not match submitted value.",
    )


class JWTClaimsModel(BaseModel):
    """Model which defines the expected JWT format"""

    aud: Literal["GHGA"]
    iss: Literal["GHGA"]
    sub: str
    iat: UTCDatetime
    exp: UTCDatetime


@pytest_asyncio.fixture(name="central_client")
async def configured_central_client(config: Config) -> AsyncGenerator[CentralClient]:
    """Yields a configured CentralClient instance"""
    async with get_configured_httpx_client(config=config) as httpx_client:
        yield CentralClient(config=config, httpx_client=httpx_client)


async def test_central_api_unavailable(config: Config, central_client):
    """Ensure an httpx.ConnectError gets raised if the central api is unavailable"""
    # Test the different public methods exposed by the CentralClient
    with pytest.raises(httpx.ConnectError):
        await central_client.fetch_new_uploads()

    with pytest.raises(httpx.ConnectError):
        await central_client.get_removable_files(file_ids=["abc123"])

    with pytest.raises(httpx.ConnectError):
        report = make_interrogation_success_report(config.storage_alias)
        await central_client.submit_interrogation_report(report=report)


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
async def test_jwt_formation(config: Config, httpx_mock: HTTPXMock):
    """Test that the CentralClient class makes proper JWTs in its requests"""
    # Create a mock JWTAuthContextProvider so we can inspect the JWT sent by this service
    central_auth_config = JWTAuthConfig(
        auth_key=DHFS_JWK.export_public(),
        auth_check_claims=dict.fromkeys(["iss", "iat", "sub", "aud", "exp"]),
    )
    auth_context_provider = JWTAuthContextProvider(
        config=central_auth_config, context_class=JWTClaimsModel
    )

    # Define a callback that can inspect the request from the central client
    callback_return_value = httpx.Response(200, json=[])

    async def callback(request: httpx.Request):
        """Callback function that decrypts the JWT in the bearer token"""
        token = cast(str, request.headers.get("Authorization"))
        token = token.removeprefix("Bearer ")
        context = await auth_context_provider.get_context(token)
        assert context
        assert context.sub == config.storage_alias
        assert context.iat - now_utc_ms_prec() < timedelta(seconds=3)
        return callback_return_value

    # Register the callback
    httpx_mock.add_callback(callback=callback)

    # Test the different methods from the CentralClient
    async with get_configured_httpx_client(config=config) as httpx_client:
        central_client = CentralClient(config=config, httpx_client=httpx_client)

        # Register the callback (see callback_return_value defined above for the response)
        httpx_mock.add_callback(callback=callback)
        await central_client.fetch_new_uploads()
        await central_client.get_removable_files(file_ids=[])

        # Update the return value for this other call
        callback_return_value = httpx.Response(201)
        report = make_interrogation_success_report(config.storage_alias)
        await central_client.submit_interrogation_report(report=report)


async def test_responses_with_bad_format(central_client, httpx_mock: HTTPXMock):
    """Test how the CentralClient handles responses that don't have the proper format.

    This affects the .fetch_new_uploads() and .get_removable_files() methods.
    """
    httpx_mock.add_response(status_code=200, json={"Not correct": "At all"})
    with pytest.raises(CentralClient.ResponseFormatError):
        await central_client.fetch_new_uploads()

    httpx_mock.add_response(status_code=200, json={"Not correct": "At all"})
    with pytest.raises(CentralClient.ResponseFormatError):
        await central_client.get_removable_files(file_ids=[])


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
async def test_500_response_handling(
    config: Config, central_client, httpx_mock: HTTPXMock
):
    """Test that "500" status codes trigger a `CentralAPIError`"""
    httpx_mock.add_response(status_code=500)
    with pytest.raises(CentralClient.CentralAPIError):
        await central_client.fetch_new_uploads()

    with pytest.raises(CentralClient.CentralAPIError):
        await central_client.get_removable_files(file_ids=[])

    with pytest.raises(CentralClient.CentralAPIError):
        report = make_interrogation_success_report(config.storage_alias)
        await central_client.submit_interrogation_report(report=report)


async def test_report_submission(config: Config, central_client, httpx_mock: HTTPXMock):
    """Test that the secret submitted inside the InterrogationReport is encrypted
    with the Central API public key, as well as that other fields are submitted.
    """
    # Define one successful and one failed interrogation report
    success_report = make_interrogation_success_report(config.storage_alias)
    fail_report = make_interrogation_failure_report(config.storage_alias)

    # Define an httpx_mock callback to let us inspect the request body
    def callback(request: httpx.Request):
        body = json.load(request)  # type: ignore
        interrogated_at = datetime.fromisoformat(body["interrogated_at"])
        assert interrogated_at - now_utc_ms_prec() < timedelta(seconds=3)
        if body["passed"]:
            secret = decrypt(body["secret"], CENTRAL_CRYPT4GH_PRIVATE_KEY)
            decoded_secret = base64.urlsafe_b64decode(secret)
            assert decoded_secret == success_report.secret.get_secret_value()  # type: ignore
            assert body["encrypted_parts_md5"]
            assert body["encrypted_parts_sha256"]
            assert not body["reason"]
        else:
            assert not body["secret"]
            assert not body["encrypted_parts_md5"]
            assert not body["encrypted_parts_sha256"]
            assert body["reason"] == fail_report.reason
        return httpx.Response(201)

    # Now make the calls
    httpx_mock.add_callback(callback)
    await central_client.submit_interrogation_report(report=success_report)
    httpx_mock.add_callback(callback)
    await central_client.submit_interrogation_report(report=fail_report)
