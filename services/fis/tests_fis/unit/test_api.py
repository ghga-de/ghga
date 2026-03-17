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

"""Unit tests for the API"""

import logging
from uuid import uuid4

import pytest
from ghga_service_commons.api.testing import AsyncTestClient
from ghga_service_commons.utils.jwt_helpers import sign_and_serialize_token
from hexkit.utils import now_utc_ms_prec
from jwcrypto.jwk import JWK

from fis.constants import GHGA
from fis.core import models
from tests_fis.fixtures.joint import JointRig
from tests_fis.fixtures.utils import create_file_under_interrogation

pytestmark = pytest.mark.asyncio()

HUB1 = "HUB1"
HUB2 = "HUB2"


class JWTTestFactory:
    """A small class that generates signed JWTs for testing based on configuration"""

    def __init__(self, data_hub_jwt_keys: dict[str, JWK]):
        """This class is for testing purposes only!"""
        self._storage_aliases = data_hub_jwt_keys

    def make_jwt(self, storage_alias: str) -> str:
        """Sign and serialize an auth token for the specified storage_alias"""
        claims: dict[str, str] = {"iss": GHGA, "aud": GHGA, "sub": storage_alias}
        assert storage_alias in self._storage_aliases, (
            f"Misuse of JWTTestFactory: {storage_alias} is not configured as a storage"
            + f"  alias. Options are: {','.join(self._storage_aliases)}"
        )
        return sign_and_serialize_token(
            claims=claims, key=self._storage_aliases[storage_alias], valid_seconds=60
        )

    def auth_header(self, storage_alias: str) -> dict[str, str]:
        """Create an auth header using the `make_jwt()` method"""
        return {"Authorization": f"Bearer {self.make_jwt(storage_alias)}"}


@pytest.fixture()
def jwt_factory(data_hub_jwks):
    """Returns a configured JWTTestFactory"""
    return JWTTestFactory(data_hub_jwks)


ROUTES_LOGGER = "fis.adapters.inbound.fastapi_.routes"
TEST_USER_AGENT = "DataHubFileService/1.0.0"


async def test_health(
    rest_client: AsyncTestClient, rig: JointRig, caplog: pytest.LogCaptureFixture
):
    """Test the GET /health endpoint"""
    url = "/health"
    response = await rest_client.get(url)
    assert response.status_code == 200

    # No User-Agent header → logged as unknown client, no storage alias
    with caplog.at_level(logging.INFO, logger=ROUTES_LOGGER):
        await rest_client.get(url, headers={"User-Agent": "Boto3/1.2.3 Python/3.12"})
    assert "Boto3/1.2.3 Python/3.12" in caplog.text
    assert "health endpoint" in caplog.text
    assert "originating from" not in caplog.text
    caplog.clear()

    # With User-Agent header → client name and version logged, still no storage alias
    with caplog.at_level(logging.INFO, logger=ROUTES_LOGGER):
        await rest_client.get(url, headers={"User-Agent": TEST_USER_AGENT})
    assert "DataHubFileService" in caplog.text
    assert "1.0.0" in caplog.text
    assert "health endpoint" in caplog.text
    assert "originating from" not in caplog.text


async def test_list_uploads(
    rest_client: AsyncTestClient,
    rig: JointRig,
    jwt_factory: JWTTestFactory,
    caplog: pytest.LogCaptureFixture,
):
    """Test the GET /storages/{storage_alias}/uploads endpoint"""
    url = f"/storages/{HUB1}/uploads"

    # Assert no auth returns a 401
    response = await rest_client.get(url)
    assert response.status_code == 401

    # Assert improper auth returns a 403
    wrong_hub_headers = jwt_factory.auth_header(HUB2)
    response = await rest_client.get(url, headers=wrong_hub_headers)
    assert response.status_code == 403

    # Verify that this works:
    correct_headers = jwt_factory.auth_header(HUB1)
    response = await rest_client.get(url, headers=correct_headers)
    assert response.status_code == 200
    assert response.json() == []

    # Verify response when files exist
    files = [create_file_under_interrogation(HUB1) for _ in range(5)]
    files_expected = [models.BaseFileInformation(**file.model_dump()) for file in files]
    for file in files:
        await rig.file_dao.insert(file)

    response = await rest_client.get(url, headers=correct_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    files_received = [models.BaseFileInformation(**item) for item in data]
    files_received_sorted = sorted(files_received, key=lambda f: f.id)
    files_expected_sorted = sorted(files_expected, key=lambda f: f.id)
    for a, b in zip(files_received_sorted, files_expected_sorted, strict=True):
        assert a.model_dump() == b.model_dump()

    # Verify user agent logging includes client name and storage alias
    with caplog.at_level(logging.INFO, logger=ROUTES_LOGGER):
        await rest_client.get(
            url,
            headers={**jwt_factory.auth_header(HUB1), "User-Agent": TEST_USER_AGENT},
        )
    assert "DataHubFileService" in caplog.text
    assert "1.0.0" in caplog.text
    assert HUB1 in caplog.text


async def test_get_removable_files(
    rest_client: AsyncTestClient,
    rig: JointRig,
    jwt_factory: JWTTestFactory,
    caplog: pytest.LogCaptureFixture,
):
    """Test the POST /storages/{storage_alias}/uploads/can_remove endpoint"""
    url = f"/storages/{HUB1}/uploads/can_remove"

    # Create test files with different can_remove states
    file_removable = create_file_under_interrogation(HUB1)
    file_removable.can_remove = True

    file_not_removable = create_file_under_interrogation(HUB1)
    file_not_removable.can_remove = False

    # Insert files into DAO
    await rig.file_dao.insert(file_removable)
    await rig.file_dao.insert(file_not_removable)

    # Create a UUID for a file that doesn't exist
    non_existent_id = uuid4()

    # Test data: list of file IDs to check
    file_ids = [file_removable.object_id, file_not_removable.object_id, non_existent_id]

    # Assert no auth returns a 401
    response = await rest_client.post(url, json=[str(id) for id in file_ids])
    assert response.status_code == 401

    # Assert improper auth returns a 403
    wrong_hub_headers = jwt_factory.auth_header(HUB2)
    response = await rest_client.post(
        url, json=[str(id) for id in file_ids], headers=wrong_hub_headers
    )
    assert response.status_code == 403

    # Verify that this works with correct auth
    correct_headers = jwt_factory.auth_header(HUB1)
    response = await rest_client.post(
        url, json=[str(id) for id in file_ids], headers=correct_headers
    )
    assert response.status_code == 200

    # Should return only the removable file and the non-existent one
    removable_ids = response.json()
    assert len(removable_ids) == 2
    assert str(file_removable.object_id) in removable_ids
    assert str(non_existent_id) in removable_ids
    assert str(file_not_removable.object_id) not in removable_ids

    # Test with empty list
    response = await rest_client.post(url, json=[], headers=correct_headers)
    assert response.status_code == 200
    assert response.json() == []

    # Verify that including a non-uuid value results in a 422
    response = await rest_client.post(url, json=["blahblah"], headers=correct_headers)
    assert response.status_code == 422

    # Verify user agent logging includes client name and storage alias
    with caplog.at_level(logging.INFO, logger=ROUTES_LOGGER):
        await rest_client.post(
            url,
            json=[],
            headers={**correct_headers, "User-Agent": TEST_USER_AGENT},
        )
    assert "DataHubFileService" in caplog.text
    assert "1.0.0" in caplog.text
    assert HUB1 in caplog.text


async def test_post_interrogation_report(
    rest_client: AsyncTestClient,
    rig: JointRig,
    jwt_factory: JWTTestFactory,
    caplog: pytest.LogCaptureFixture,
):
    """Test the POST /storages/{storage_alias}/interrogation-reports endpoint"""
    url = f"/storages/{HUB1}/interrogation-reports"

    # Create a file in the DAO that we can report on
    file = create_file_under_interrogation(HUB1)
    await rig.file_dao.insert(file)

    # Create a successful interrogation report
    success_report = {
        "file_id": str(file.id),
        "storage_alias": file.storage_alias,
        "bucket_id": "interrogation1",
        "object_id": str(file.object_id),
        "interrogated_at": now_utc_ms_prec().isoformat(),
        "passed": True,
        "secret": "c2VjcmV0X2RhdGFfaGVyZQ==",
        "encrypted_parts_md5": ["abc123", "def456"],
        "encrypted_parts_sha256": ["sha256_1", "sha256_2"],
        "encrypted_size": 1234,
    }

    # Make sure that not supplying auth headers returns 401
    response = await rest_client.post(url, json=success_report)
    assert response.status_code == 401

    # Make sure that supplying an invalid token for another hub returns 403
    wrong_hub_headers = jwt_factory.auth_header(HUB2)
    response = await rest_client.post(
        url, json=success_report, headers=wrong_hub_headers
    )
    assert response.status_code == 403

    # Submit interrogation report with valid token
    correct_headers = jwt_factory.auth_header(HUB1)
    response = await rest_client.post(url, json=success_report, headers=correct_headers)
    assert response.status_code == 201

    # Verify that FIS updated the state of the FileUnderInterrogation object
    updated_file = await rig.file_dao.get_by_id(file.id)
    assert updated_file.interrogated is True
    assert updated_file.state == "interrogated"

    # Create another file for failed interrogation
    file2 = create_file_under_interrogation(HUB1)
    await rig.file_dao.insert(file2)

    # Create a failed interrogation report
    failure_report = {
        "file_id": str(file2.id),
        "storage_alias": file2.storage_alias,
        "interrogated_at": now_utc_ms_prec().isoformat(),
        "passed": False,
        "reason": "Checksum mismatch",
    }

    # Test failed interrogation report
    response = await rest_client.post(url, json=failure_report, headers=correct_headers)
    assert response.status_code == 201

    # Verify file was updated and marked for removal
    updated_file2 = await rig.file_dao.get_by_id(file2.id)
    assert updated_file2.interrogated is True
    assert updated_file2.state == "failed"
    assert updated_file2.can_remove is True

    # Test file not found returns 404
    non_existent_report = success_report.copy()
    non_existent_report.update({"file_id": str(uuid4())})
    response = await rest_client.post(
        url, json=non_existent_report, headers=correct_headers
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # Test validation error: passed=True without checksums
    invalid_success_report = {
        "file_id": str(file.id),
        "storage_alias": file.storage_alias,
        "bucket_id": "interrogation1",
        "interrogated_at": now_utc_ms_prec().isoformat(),
        "passed": True,
        "secret": "c2VjcmV0X2RhdGFfaGVyZQ==",
    }
    response = await rest_client.post(
        url, json=invalid_success_report, headers=correct_headers
    )
    assert response.status_code == 422

    # Test validation error: passed=False without reason
    invalid_failure_report = {
        "file_id": str(file2.id),
        "storage_alias": file2.storage_alias,
        "interrogated_at": now_utc_ms_prec().isoformat(),
        "passed": False,
    }
    response = await rest_client.post(
        url, json=invalid_failure_report, headers=correct_headers
    )
    assert response.status_code == 422

    # Verify user agent logging includes client name and storage alias
    with caplog.at_level(logging.INFO, logger=ROUTES_LOGGER):
        await rest_client.post(
            url,
            json=success_report,
            headers={**correct_headers, "User-Agent": TEST_USER_AGENT},
        )
    assert "DataHubFileService" in caplog.text
    assert "1.0.0" in caplog.text
    assert HUB1 in caplog.text
