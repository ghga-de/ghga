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

"""Tests typical user journeys"""

import logging

import ghga_event_schemas.pydantic_ as event_schemas
import pytest
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.protocols.dao import ResourceNotFoundError

from dins.core import models
from tests.fixtures.joint import (
    JointFixture,
    joint_fixture,  # noqa: F401
    kafka_container_fixture,  # noqa: F401
    kafka_fixture,  # noqa: F401
    mongodb_container_fixture,  # noqa: F401
    mongodb_fixture,  # noqa: F401
)

FILE_ID = "test-file"
CHANGED_TYPE = "upserted"
DECRYPTED_SHA256 = "fake-checksum"
DECRYPTED_SIZE = 12345678

INCOMING_PAYLOAD_MOCK = event_schemas.FileInternallyRegistered(
    s3_endpoint_alias="test-node",
    file_id=FILE_ID,
    object_id="test-object",
    bucket_id="test-bucket",
    upload_date=now_as_utc().isoformat(),
    decrypted_size=DECRYPTED_SIZE,
    decrypted_sha256=DECRYPTED_SHA256,
    encrypted_part_size=1,
    encrypted_parts_md5=["some", "checksum"],
    encrypted_parts_sha256=["some", "checksum"],
    content_offset=1234,
    decryption_secret_id="some-secret",
)

FILE_INFORMATION_MOCK = models.FileInformation(
    file_id=FILE_ID, sha256_hash=DECRYPTED_SHA256, size=DECRYPTED_SIZE
)

pytestmark = pytest.mark.asyncio()


async def test_normal_journey(
    joint_fixture: JointFixture,  # noqa: F811
    caplog,
):
    """Simulates a typical, successful API journey."""
    # Test population path
    file_id = INCOMING_PAYLOAD_MOCK.file_id

    await joint_fixture.kafka.publish_event(
        payload=INCOMING_PAYLOAD_MOCK.model_dump(),
        type_=joint_fixture.config.file_registered_event_type,
        topic=joint_fixture.config.file_registered_event_topic,
    )
    await joint_fixture.event_subscriber.run(forever=False)

    file_information = await joint_fixture.file_information_dao.get_by_id(file_id)
    assert file_information == FILE_INFORMATION_MOCK

    # Test reregistration of identical content
    expected_message = f"Found existing information for file {file_id}"

    caplog.clear()
    with caplog.at_level(level=logging.DEBUG, logger="dins.core.information_service"):
        await joint_fixture.kafka.publish_event(
            payload=INCOMING_PAYLOAD_MOCK.model_dump(),
            type_=joint_fixture.config.file_registered_event_type,
            topic=joint_fixture.config.file_registered_event_topic,
        )
        await joint_fixture.event_subscriber.run(forever=False)
        assert len(caplog.messages) == 1
        assert expected_message in caplog.messages

    # Test reregistration of mismatching content
    mismatch_message = f"Mismatching information for the file with ID {file_id}"
    "has already been registered."
    mismatch_mock = INCOMING_PAYLOAD_MOCK.model_copy(
        update={"decrypted_sha256": "other-fake-checksum"}
    )

    caplog.clear()
    with caplog.at_level(level=logging.DEBUG, logger="dins.core.information_service"):
        await joint_fixture.kafka.publish_event(
            payload=mismatch_mock.model_dump(),
            type_=joint_fixture.config.file_registered_event_type,
            topic=joint_fixture.config.file_registered_event_topic,
        )
        await joint_fixture.event_subscriber.run(forever=False)
        assert len(caplog.messages) == 2
        assert expected_message in caplog.messages
        assert mismatch_message in caplog.messages

    # Test requesting existing file information
    base_url = f"{joint_fixture.config.api_root_path}/file_information"
    url = f"{base_url}/{file_id}"
    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == 200
    assert models.FileInformation(**response.json()) == FILE_INFORMATION_MOCK

    # Test requesting invalid file information
    url = f"{base_url}/invalid"
    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == 404

    # request deletion
    deletion_requested = event_schemas.FileDeletionRequested(file_id=file_id)

    await joint_fixture.kafka.publish_event(
        payload=deletion_requested.model_dump(),
        type_=CHANGED_TYPE,
        topic=joint_fixture.config.files_to_delete_topic,
    )
    await joint_fixture.outbox_subscriber.run(forever=False)

    # assert information is gone
    with pytest.raises(ResourceNotFoundError):
        file_information = await joint_fixture.file_information_dao.get_by_id(
            id_=file_id
        )
