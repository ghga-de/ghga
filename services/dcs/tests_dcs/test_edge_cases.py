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

"""Tests edge cases not covered by the typical journey test."""

from dataclasses import dataclass
from uuid import uuid4

import httpx2
import pytest
import pytest_asyncio
from fastapi import status
from pydantic import UUID4

from dcs.core import models
from dcs.core.errors import StorageAliasNotConfiguredError
from dcs.ports.outbound.dao import DrsObjectDaoPort
from hexkit.utils import now_utc_ms_prec
from tests_dcs.fixtures.ekss_api import (
    ResponseHandler,
    fail_to_connect,
    secret_not_found,
)
from tests_dcs.fixtures.joint import EXAMPLE_FILE, JointFixture, PopulatedFixture
from tests_dcs.fixtures.utils import (
    generate_token_signing_keys,
    generate_work_order_token,
)

pytestmark = pytest.mark.asyncio()


@dataclass
class StorageUnavailableFixture:
    """Fixture to provide DRS DB entry with misconfigured storage alias"""

    mongodb_dao: DrsObjectDaoPort
    joint: JointFixture
    file_id: UUID4


@pytest_asyncio.fixture
async def storage_unavailable_fixture(joint_fixture: JointFixture):
    """Set up file with unavailable storage alias"""
    test_file = EXAMPLE_FILE.model_copy(deep=True)
    test_file.file_id = uuid4()
    test_file.storage_alias = joint_fixture.endpoint_aliases.fake_node

    # populate DB entry
    mongodb_dao = await joint_fixture.mongodb.dao_factory.get_dao(
        name="drs_objects",
        dto_model=models.AccessTimeDrsObject,
        id_field="file_id",
    )
    await mongodb_dao.insert(test_file)

    yield StorageUnavailableFixture(
        mongodb_dao=mongodb_dao,
        joint=joint_fixture,
        file_id=test_file.file_id,
    )


async def test_get_health(joint_fixture: JointFixture):
    """Test the GET /health endpoint"""
    response = await joint_fixture.rest_client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "OK"}


async def test_access_non_existing(joint_fixture: JointFixture):
    """Checks that requesting access to a non-existing DRS object fails with the
    expected exception.
    """
    accession = "GHGADoesNotExist"
    file_id = uuid4()

    work_order_token = generate_work_order_token(
        file_id=file_id, accession=accession, jwk=joint_fixture.jwk
    )
    wrong_jwk = generate_token_signing_keys()
    wrong_work_order_token = generate_work_order_token(
        file_id=file_id, accession=accession, jwk=wrong_jwk
    )

    # test with missing authorization header
    # (should not expose whether the file with the given id exists or not)
    response = await joint_fixture.rest_client.get(
        f"/objects/{accession}",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # test with authorization header but wrong pubkey
    response = await joint_fixture.rest_client.get(
        f"/objects/{accession}",
        timeout=5,
        headers={"Authorization": f"Bearer {wrong_work_order_token}"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # test with correct authorization header but wrong object_id
    response = await joint_fixture.rest_client.get(
        f"/objects/{accession}",
        timeout=5,
        headers={"Authorization": f"Bearer {work_order_token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

    response = await joint_fixture.rest_client.get(
        f"/objects/{accession}/envelopes",
        timeout=5,
        headers={"Authorization": f"Bearer {work_order_token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_deletion_config_error(
    storage_unavailable_fixture: StorageUnavailableFixture,
):
    """Simulate a deletion request for a file with an unconfigured storage alias."""
    data_repository = storage_unavailable_fixture.joint.data_repository
    with pytest.raises(StorageAliasNotConfiguredError):
        await data_repository.delete_file(file_id=storage_unavailable_fixture.file_id)


async def test_drs_config_error(
    storage_unavailable_fixture: StorageUnavailableFixture,
):
    """Test DRS endpoint for a storage alias that is not configured"""
    # generate work order token
    accession = "GHGA001"
    work_order_token = generate_work_order_token(
        accession=accession,
        file_id=storage_unavailable_fixture.file_id,
        jwk=storage_unavailable_fixture.joint.jwk,
        valid_seconds=120,
    )

    # modify default headers:
    storage_unavailable_fixture.joint.rest_client.headers = httpx2.Headers(
        {"Authorization": f"Bearer {work_order_token}"}
    )

    response = await storage_unavailable_fixture.joint.rest_client.get(
        f"/objects/{accession}", timeout=5
    )
    assert response.status_code == 500


@pytest.mark.parametrize(
    "on_get_envelope",
    [fail_to_connect(), secret_not_found()],
    ids=["unreachable", "secret_not_found"],
)
async def test_envelope_request_with_failing_ekss(
    populated_fixture: PopulatedFixture,
    on_get_envelope: ResponseHandler,
):
    """Both an unreachable EKSS and an unknown secret surface as a 500."""
    joint_fixture = populated_fixture.joint_fixture
    joint_fixture.ekss.on_get_envelope = on_get_envelope

    accession = "GHGA001"
    work_order_token = generate_work_order_token(
        accession=accession,
        file_id=populated_fixture.example_file.file_id,
        jwk=joint_fixture.jwk,
        valid_seconds=120,
    )
    joint_fixture.rest_client.headers = httpx2.Headers(
        {"Authorization": f"Bearer {work_order_token}"}
    )

    response = await joint_fixture.rest_client.get(
        f"/objects/{accession}/envelopes", timeout=5
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert joint_fixture.ekss.requests, "the EKSS mock was never called"


async def test_register_file_twice(populated_fixture: PopulatedFixture, caplog):
    """Assure that files cannot be registered twice"""
    joint_fixture = populated_fixture.joint_fixture
    example_file = populated_fixture.example_file

    file = models.DrsObjectBase(
        file_id=example_file.file_id,
        secret_id=example_file.secret_id,
        decrypted_sha256=example_file.decrypted_sha256,
        decrypted_size=example_file.decrypted_size,
        creation_date=now_utc_ms_prec(),
        encrypted_size=example_file.encrypted_size,
        storage_alias=example_file.storage_alias,
    )

    caplog.clear()
    await joint_fixture.data_repository.register_new_file(file=file)
    failure_message = f"Could not register file with id '{
        example_file.file_id
    }' as an entry already exists for this id."
    assert failure_message in caplog.messages
