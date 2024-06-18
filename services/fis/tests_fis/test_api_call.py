# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test actual API call and event publishing"""

import base64
import json
import os

import pytest
from fis.core.models import EncryptedPayload, LegacyUploadMetadata, UploadMetadata
from ghga_event_schemas.pydantic_ import FileUploadValidationSuccess
from ghga_service_commons.utils.crypt import encrypt
from hexkit.providers.akafka.testutils import (
    EventRecorder,
    ExpectedEvent,
    check_recorded_events,
)

from tests_fis.fixtures.joint import TEST_PAYLOAD, JointFixture

pytestmark = pytest.mark.asyncio()


async def test_health_check(joint_fixture: JointFixture):
    """Test that the health check endpoint works."""
    response = await joint_fixture.rest_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "OK"}


async def test_api_calls(monkeypatch, joint_fixture: JointFixture):
    """Test functionality with incoming API call"""
    file_secret = base64.b64encode(os.urandom(32)).decode("utf-8")
    secret_id = "test_secret_id"
    headers = {"Authorization": f"Bearer {joint_fixture.token}"}

    encrypted_secret = EncryptedPayload(
        payload=encrypt(data=file_secret, key=joint_fixture.keypair.public)
    )

    # test secret storage call
    with monkeypatch.context() as patch:
        # patch vault call with mock
        patch.setattr(
            "fis.adapters.outbound.vault.client.VaultAdapter.store_secret",
            lambda self, secret: secret_id,
        )
        response = await joint_fixture.rest_client.post(
            "/federated/ingest_secret",
            json=encrypted_secret.model_dump(),
            headers=headers,
        )

    assert response.status_code == 200
    obtained_secret_id = json.loads(response.content)["secret_id"]
    assert secret_id == obtained_secret_id

    # test missing authorization
    response = await joint_fixture.rest_client.post(
        "/federated/ingest_metadata", json=encrypted_secret.model_dump()
    )
    assert response.status_code == 403

    # test malformed payload
    nonsense_payload = encrypted_secret.model_copy(update={"payload": "abcdefghijklmn"})
    response = await joint_fixture.rest_client.post(
        "/federated/ingest_metadata",
        json=nonsense_payload.model_dump(),
        headers=headers,
    )
    assert response.status_code == 422

    # test metadata ingest path
    payload = UploadMetadata(
        **TEST_PAYLOAD.model_dump(),
        secret_id=secret_id,
    )
    encrypted_payload = EncryptedPayload(
        payload=encrypt(
            data=payload.model_dump_json(),
            key=joint_fixture.keypair.public,
        )
    )

    event_recorder = EventRecorder(
        kafka_servers=joint_fixture.kafka.config.kafka_servers,
        topic=joint_fixture.config.file_upload_validation_success_topic,
    )

    async with event_recorder:
        response = await joint_fixture.rest_client.post(
            "/federated/ingest_metadata",
            json=encrypted_payload.model_dump(),
            headers=headers,
        )

    assert response.status_code == 202
    assert len(event_recorder.recorded_events) == 1

    # can't get exact event time for equality comparison, don't check but get directly
    # from the recorded event instead
    expected_upload_date = str(event_recorder.recorded_events[0].payload["upload_date"])

    payload = FileUploadValidationSuccess(
        upload_date=expected_upload_date,
        file_id=TEST_PAYLOAD.file_id,
        object_id=TEST_PAYLOAD.object_id,
        bucket_id=joint_fixture.config.source_bucket_id,
        s3_endpoint_alias=joint_fixture.s3_endpoint_alias,
        decrypted_size=TEST_PAYLOAD.unencrypted_size,
        decryption_secret_id=secret_id,
        content_offset=0,
        encrypted_part_size=TEST_PAYLOAD.part_size,
        encrypted_parts_md5=TEST_PAYLOAD.encrypted_md5_checksums,
        encrypted_parts_sha256=TEST_PAYLOAD.encrypted_sha256_checksums,
        decrypted_sha256=TEST_PAYLOAD.unencrypted_checksum,
    )

    expected_event = ExpectedEvent(
        payload=payload.model_dump(),
        type_="upserted",
        key=TEST_PAYLOAD.file_id,
    )

    check_recorded_events(
        recorded_events=event_recorder.recorded_events, expected_events=[expected_event]
    )

    # test missing authorization
    response = await joint_fixture.rest_client.post(
        "/federated/ingest_metadata", json=encrypted_payload.model_dump()
    )
    assert response.status_code == 403

    # test malformed payload
    nonsense_payload = encrypted_payload.model_copy(
        update={"payload": "abcdefghijklmn"}
    )
    response = await joint_fixture.rest_client.post(
        "/federated/ingest_metadata",
        json=nonsense_payload.model_dump(),
        headers=headers,
    )
    assert response.status_code == 422


async def test_legacy_api_calls(monkeypatch, joint_fixture: JointFixture):
    """Test functionality with incoming API call"""
    payload = LegacyUploadMetadata(
        **TEST_PAYLOAD.model_dump(),
        file_secret=base64.b64encode(os.urandom(32)).decode("utf-8"),
    )
    encrypted_payload = EncryptedPayload(
        payload=encrypt(
            data=payload.model_dump_json(),
            key=joint_fixture.keypair.public,
        )
    )

    event_recorder = EventRecorder(
        kafka_servers=joint_fixture.kafka.config.kafka_servers,
        topic=joint_fixture.config.file_upload_validation_success_topic,
    )
    secret_id = "very_secret_id"

    # test happy path
    headers = {"Authorization": f"Bearer {joint_fixture.token}"}

    # patch vault call with mock
    with monkeypatch.context() as patch:
        patch.setattr(
            "fis.adapters.outbound.vault.client.VaultAdapter.store_secret",
            lambda self, secret: secret_id,
        )

        async with event_recorder:
            response = await joint_fixture.rest_client.post(
                "/legacy/ingest",
                json=encrypted_payload.model_dump(),
                headers=headers,
            )

    assert response.status_code == 202
    assert len(event_recorder.recorded_events) == 1

    # can't get exact event time for equality comparison, don't check but get directly
    # from the recorded event instead
    expected_upload_date = str(event_recorder.recorded_events[0].payload["upload_date"])

    payload = FileUploadValidationSuccess(
        upload_date=expected_upload_date,
        file_id=TEST_PAYLOAD.file_id,
        object_id=TEST_PAYLOAD.object_id,
        bucket_id=joint_fixture.config.source_bucket_id,
        s3_endpoint_alias=joint_fixture.s3_endpoint_alias,
        decrypted_size=TEST_PAYLOAD.unencrypted_size,
        decryption_secret_id=secret_id,
        content_offset=0,
        encrypted_part_size=TEST_PAYLOAD.part_size,
        encrypted_parts_md5=TEST_PAYLOAD.encrypted_md5_checksums,
        encrypted_parts_sha256=TEST_PAYLOAD.encrypted_sha256_checksums,
        decrypted_sha256=TEST_PAYLOAD.unencrypted_checksum,
    )

    expected_event = ExpectedEvent(
        payload=payload.model_dump(),
        type_="upserted",
        key=TEST_PAYLOAD.file_id,
    )

    check_recorded_events(
        recorded_events=event_recorder.recorded_events, expected_events=[expected_event]
    )

    # test missing authorization
    response = await joint_fixture.rest_client.post(
        "/legacy/ingest", json=encrypted_payload.model_dump()
    )
    assert response.status_code == 403

    # test malformed payload
    nonsense_payload = encrypted_payload.model_copy(
        update={"payload": "abcdefghijklmn"}
    )
    response = await joint_fixture.rest_client.post(
        "/legacy/ingest", json=nonsense_payload.model_dump(), headers=headers
    )
    assert response.status_code == 422
