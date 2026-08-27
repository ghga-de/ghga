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

"""Unit tests for the CentralClient"""

import base64
import json
import os
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import Literal
from uuid import uuid4

import httpx2
import pytest
import pytest_asyncio
from pydantic import BaseModel, SecretBytes

from dhfs import __version__
from dhfs.adapters.outbound.central import CentralClient
from dhfs.adapters.outbound.http import (
    ConnectionFailedError,
    get_configured_httpx_client,
)
from dhfs.config import Config
from dhfs.core.models import InterrogationReport
from ghga_service_commons.api.mock_api import respond
from ghga_service_commons.auth.jwt_auth import JWTAuthConfig, JWTAuthContextProvider
from ghga_service_commons.utils.crypt import decrypt
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.utils import now_utc_ms_prec
from tests.fixtures.central_api import CentralApiMock
from tests.fixtures.utils import CENTRAL_CRYPT4GH_PRIVATE_KEY, DHFS_JWK

pytestmark = pytest.mark.asyncio()


def make_interrogation_success_report(storage_alias: str) -> InterrogationReport:
    """Creates a successful InterrogationReport with the requested storage alias value"""
    return InterrogationReport(
        file_id=uuid4(),
        storage_alias=storage_alias,
        bucket_id="hub1-interrogation",
        object_id=uuid4(),
        interrogated_at=now_utc_ms_prec(),
        passed=True,
        secret=SecretBytes(os.urandom(32)),
        encrypted_parts_md5=["abc123", "def456", "ghi789"],
        encrypted_parts_sha256=["123abc", "456def", "789ghi"],
        encrypted_size=1000,
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


@pytest.fixture(name="central_api")
def central_api_fixture(config: Config) -> CentralApiMock:
    """Yields a mock of the GHGA Central API"""
    return CentralApiMock(config=config)


@pytest_asyncio.fixture(name="central_client")
async def configured_central_client(
    config: Config, central_api: CentralApiMock
) -> AsyncGenerator[CentralClient]:
    """Yields a CentralClient instance talking to the mocked Central API"""
    async with get_configured_httpx_client(
        config=config, base_transport=central_api.as_transport()
    ) as httpx_client:
        yield CentralClient(config=config, httpx_client=httpx_client)


async def test_central_api_unavailable(config: Config):
    """Ensure a ConnectionFailedError gets raised if the central api is unavailable"""
    # Use an unmocked client so the requests actually fail to connect
    async with get_configured_httpx_client(config=config) as httpx_client:
        central_client = CentralClient(config=config, httpx_client=httpx_client)

        # Test the different public methods exposed by the CentralClient
        with pytest.raises(ConnectionFailedError):
            await central_client.fetch_new_uploads()

        with pytest.raises(ConnectionFailedError):
            await central_client.get_removable_files(object_ids=["abc123"])

        with pytest.raises(ConnectionFailedError):
            report = make_interrogation_success_report(config.storage_alias)
            await central_client.submit_interrogation_report(report=report)


async def test_jwt_formation(
    config: Config, central_client: CentralClient, central_api: CentralApiMock
):
    """Test that the CentralClient class makes proper JWTs in its requests"""
    # Create a JWTAuthContextProvider so we can inspect the JWTs sent by this service
    central_auth_config = JWTAuthConfig(
        auth_key=DHFS_JWK.export_public(),
        auth_check_claims=dict.fromkeys(["iss", "iat", "sub", "aud", "exp"]),
    )
    auth_context_provider = JWTAuthContextProvider(
        config=central_auth_config, context_class=JWTClaimsModel
    )

    # Exercise the different methods from the CentralClient
    await central_client.fetch_new_uploads()
    await central_client.get_removable_files(object_ids=[])
    report = make_interrogation_success_report(config.storage_alias)
    await central_client.submit_interrogation_report(report=report)

    # Inspect the bearer token of every request that reached the Central API
    assert len(central_api.requests) == 3
    for request in central_api.requests:
        token = request.headers["Authorization"].removeprefix("Bearer ")
        context = await auth_context_provider.get_context(token)
        assert context
        assert context.sub == config.storage_alias
        assert context.iat - now_utc_ms_prec() < timedelta(seconds=3)


async def test_responses_with_bad_format(
    central_client: CentralClient, central_api: CentralApiMock
):
    """Test how the CentralClient handles responses that don't have the proper format.

    This affects the .fetch_new_uploads() and .get_removable_files() methods.
    """
    central_api.on_fetch_new_uploads = respond(200, json={"Not correct": "At all"})
    with pytest.raises(CentralClient.ResponseFormatError):
        await central_client.fetch_new_uploads()

    central_api.on_get_removable_files = respond(200, json={"Not correct": "At all"})
    with pytest.raises(CentralClient.ResponseFormatError):
        await central_client.get_removable_files(object_ids=[])


async def test_500_response_handling(
    config: Config, central_client: CentralClient, central_api: CentralApiMock
):
    """Test that "500" status codes trigger a `CentralAPIError`"""
    central_api.on_fetch_new_uploads = respond(500)
    central_api.on_get_removable_files = respond(500)
    central_api.on_submit_report = respond(500)

    with pytest.raises(CentralClient.CentralAPIError):
        await central_client.fetch_new_uploads()

    with pytest.raises(CentralClient.CentralAPIError):
        await central_client.get_removable_files(object_ids=[])

    with pytest.raises(CentralClient.CentralAPIError):
        report = make_interrogation_success_report(config.storage_alias)
        await central_client.submit_interrogation_report(report=report)


async def test_426_response_handling(
    config: Config, central_client: CentralClient, central_api: CentralApiMock
):
    """Test that 426 responses trigger a CentralAPIError and log the upgrade message."""
    central_api.on_fetch_new_uploads = respond(426)
    central_api.on_get_removable_files = respond(426)
    central_api.on_submit_report = respond(426)

    with pytest.raises(CentralClient.UpgradeRequiredError):
        await central_client.fetch_new_uploads()

    with pytest.raises(CentralClient.UpgradeRequiredError):
        await central_client.get_removable_files(object_ids=[])

    with pytest.raises(CentralClient.UpgradeRequiredError):
        report = make_interrogation_success_report(config.storage_alias)
        await central_client.submit_interrogation_report(report=report)


async def test_report_submission(
    config: Config, central_client: CentralClient, central_api: CentralApiMock
):
    """Test that the secret submitted inside the InterrogationReport is encrypted
    with the Central API public key, as well as that other fields are submitted.
    """
    # Define one successful and one failed interrogation report
    success_report = make_interrogation_success_report(config.storage_alias)
    fail_report = make_interrogation_failure_report(config.storage_alias)

    # Define a handler to let us inspect the request body
    def inspect_report(
        request: httpx2.Request, **path_variables: str
    ) -> httpx2.Response:
        user_agent = request.headers.get("User-Agent")
        assert user_agent == f"GHGA DataHubFileService/{__version__}"
        body = json.loads(request.content)
        interrogated_at = datetime.fromisoformat(body["interrogated_at"])
        assert interrogated_at - now_utc_ms_prec() < timedelta(seconds=3)
        if body["passed"]:
            secret = decrypt(body["secret"], CENTRAL_CRYPT4GH_PRIVATE_KEY)
            decoded_secret = base64.urlsafe_b64decode(secret)
            assert decoded_secret == success_report.secret.get_secret_value()  # type: ignore
            assert isinstance(body["encrypted_parts_md5"], list)
            assert all(isinstance(c, str) for c in body["encrypted_parts_md5"])
            assert isinstance(body["encrypted_parts_sha256"], list)
            assert all(isinstance(c, str) for c in body["encrypted_parts_sha256"])
            assert body["encrypted_size"]
            assert isinstance(body["encrypted_size"], int)
            assert not body["reason"]
        else:
            assert not body["secret"]
            assert not body["encrypted_parts_md5"]
            assert not body["encrypted_parts_sha256"]
            assert not body["encrypted_size"]
            assert body["reason"] == fail_report.reason
        return httpx2.Response(201)

    # Now make the calls
    central_api.on_submit_report = inspect_report
    await central_client.submit_interrogation_report(report=success_report)
    await central_client.submit_interrogation_report(report=fail_report)

    assert len(central_api.requests) == 2
