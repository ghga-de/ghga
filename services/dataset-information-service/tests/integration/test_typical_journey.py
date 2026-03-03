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

"""Tests typical user journeys"""

import logging

import ghga_event_schemas.pydantic_ as event_schemas
import pytest
from hexkit.protocols.dao import ResourceNotFoundError

from dins.adapters.outbound.dao import get_file_accession_map_dao
from dins.core import models
from tests.fixtures.joint import JointFixture
from tests.fixtures.utils import (
    ACCESSION1,
    ACCESSION2,
    ACCESSION3,
    DECRYPTED_SHA256,
    DECRYPTED_SIZE,
    FILE_ID_1,
    FILE_ID_2,
    FILE_ID_3,
    make_accession_map,
    make_file_internally_registered,
    make_metadata_dataset_overview,
)

pytestmark = pytest.mark.asyncio

FILE_1 = event_schemas.MetadataDatasetFile(
    accession=ACCESSION1, description="Test File 1", file_extension=".zip"
)
FILE_2 = event_schemas.MetadataDatasetFile(
    accession=ACCESSION2, description="Test File 2", file_extension=".zip"
)
FILE_3 = event_schemas.MetadataDatasetFile(
    accession=ACCESSION3, description="Test File 3", file_extension=".zip"
)

INCOMING_DATASET_PAYLOAD = make_metadata_dataset_overview(
    accession="GHGAtest-dataset",
    files=[FILE_1, FILE_2],
)

UPDATE_DATASET_PAYLOAD = make_metadata_dataset_overview(
    accession="GHGAtest-dataset",
    files=[FILE_1, FILE_2, FILE_3],
)

INCOMING_FILE_PAYLOAD = make_file_internally_registered(
    file_id=FILE_ID_1,
    storage_alias="test-node",
    decrypted_sha256=DECRYPTED_SHA256,
    decrypted_size=DECRYPTED_SIZE,
)
INCOMING_FILE_PAYLOAD_2 = make_file_internally_registered(
    file_id=FILE_ID_2,
    storage_alias="test-node-2",
    decrypted_sha256=DECRYPTED_SHA256,
    decrypted_size=DECRYPTED_SIZE,
)
INCOMING_FILE_PAYLOAD_3 = make_file_internally_registered(
    file_id=FILE_ID_3,
    storage_alias="test-node-3",
    decrypted_sha256=DECRYPTED_SHA256,
    decrypted_size=DECRYPTED_SIZE,
)

ACCESSION_MAP_1 = make_accession_map(accession=ACCESSION1, file_id=FILE_ID_1)
ACCESSION_MAP_2 = make_accession_map(accession=ACCESSION2, file_id=FILE_ID_2)
ACCESSION_MAP_3 = make_accession_map(accession=ACCESSION3, file_id=FILE_ID_3)

FILE_INFORMATION = models.FileInformation(
    accession=ACCESSION1,
    sha256_hash=DECRYPTED_SHA256,
    size=DECRYPTED_SIZE,
    storage_alias="test-node",
)


async def test_file_information_journey(joint_fixture: JointFixture, caplog):
    """Simulates a typical file information API journey."""
    # Publish FileInternallyRegistered - no accession map yet, so stores PendingFileInfo
    await joint_fixture.kafka.publish_event(
        payload=INCOMING_FILE_PAYLOAD.model_dump(),
        type_=joint_fixture.config.file_internally_registered_type,
        topic=joint_fixture.config.file_internally_registered_topic,
    )
    await joint_fixture.event_subscriber.run(forever=False)

    # Store the accession map - merges PendingFileInfo into FileInformation
    await joint_fixture.information_service.store_accession_map(
        accession_map=ACCESSION_MAP_1
    )

    file_information = await joint_fixture.file_information_dao.get_by_id(ACCESSION1)
    assert file_information == FILE_INFORMATION

    # Test reregistration of identical content
    expected_message = f"Found existing information for file {ACCESSION1}."

    caplog.clear()
    with caplog.at_level(level=logging.DEBUG, logger="dins.core.information_service"):
        await joint_fixture.kafka.publish_event(
            payload=INCOMING_FILE_PAYLOAD.model_dump(),
            type_=joint_fixture.config.file_internally_registered_type,
            topic=joint_fixture.config.file_internally_registered_topic,
        )
        await joint_fixture.event_subscriber.run(forever=False)
        assert len(caplog.messages) == 1
        assert expected_message in caplog.messages

    # Test reregistration of mismatching content
    mismatch_message = (
        f"Mismatching information for the file with accession {ACCESSION1} has already"
        + " been registered."
    )
    mismatch_mock = INCOMING_FILE_PAYLOAD.model_copy(
        update={"decrypted_sha256": "other-fake-checksum"}
    )

    caplog.clear()
    with caplog.at_level(level=logging.DEBUG, logger="dins.core.information_service"):
        await joint_fixture.kafka.publish_event(
            payload=mismatch_mock.model_dump(),
            type_=joint_fixture.config.file_internally_registered_type,
            topic=joint_fixture.config.file_internally_registered_topic,
        )
        await joint_fixture.event_subscriber.run(forever=False)
        service_messages = [
            r.getMessage()
            for r in caplog.records
            if r.name == "dins.core.information_service"
        ]
        assert len(service_messages) == 2
        assert expected_message in service_messages
        assert mismatch_message in service_messages

    # Test requesting existing file information
    base_url = f"{joint_fixture.config.api_root_path}/file_information"
    url = f"{base_url}/{ACCESSION1}"
    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == 200
    assert models.FileInformation(**response.json()) == FILE_INFORMATION

    # Test requesting invalid file information
    url = f"{base_url}/invalid"
    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == 404

    # Request deletion - file_id is the UUID, not the accession
    deletion_requested = models.FileDeletionRequested(file_id=FILE_ID_1)

    await joint_fixture.kafka.publish_event(
        payload=deletion_requested.model_dump(),
        type_=joint_fixture.config.file_deletion_request_type,
        topic=joint_fixture.config.file_deletion_request_topic,
    )
    await joint_fixture.event_subscriber.run(forever=False)

    # assert information is gone
    with pytest.raises(ResourceNotFoundError):
        await joint_fixture.file_information_dao.get_by_id(ACCESSION1)


async def test_dataset_information_journey(
    joint_fixture: JointFixture,
    caplog,
):
    """Simulates a typical dataset information API journey."""
    # register dataset and verify
    await joint_fixture.kafka.publish_event(
        payload=INCOMING_DATASET_PAYLOAD.model_dump(),
        type_=joint_fixture.config.dataset_upsertion_type,
        topic=joint_fixture.config.dataset_change_topic,
    )
    await joint_fixture.event_subscriber.run(forever=False)

    dataset_accession = INCOMING_DATASET_PAYLOAD.accession
    dataset = await joint_fixture.dataset_dao.get_by_id(dataset_accession)
    assert dataset.accession == dataset_accession
    for file in INCOMING_DATASET_PAYLOAD.files:
        assert file.accession in dataset.file_accessions

    base_url = f"{joint_fixture.config.api_root_path}/dataset_information"
    url = f"{base_url}/{dataset_accession}"
    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == 200

    dataset_information = response.json()
    assert dataset_information["accession"] == dataset_accession
    assert dataset_information["file_information"] == [
        {"accession": ACCESSION1},
        {"accession": ACCESSION2},
    ]

    # Register files internally - stores PendingFileInfo, no FileInformation yet
    for file_payload in (
        INCOMING_FILE_PAYLOAD,
        INCOMING_FILE_PAYLOAD_2,
        INCOMING_FILE_PAYLOAD_3,
    ):
        await joint_fixture.kafka.publish_event(
            payload=file_payload.model_dump(),
            type_=joint_fixture.config.file_internally_registered_type,
            topic=joint_fixture.config.file_internally_registered_topic,
        )
        await joint_fixture.event_subscriber.run(forever=False)

    # Store accession maps - merges each PendingFileInfo into FileInformation
    for accession_map in (ACCESSION_MAP_1, ACCESSION_MAP_2, ACCESSION_MAP_3):
        await joint_fixture.information_service.store_accession_map(
            accession_map=accession_map
        )

    # check again to verify that correct file information is returned now
    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == 200

    dataset_information = response.json()
    assert dataset_information["accession"] == dataset_accession
    assert dataset_information["file_information"] == [
        {
            "accession": ACCESSION1,
            "size": DECRYPTED_SIZE,
            "sha256_hash": DECRYPTED_SHA256,
            "storage_alias": "test-node",
        },
        {
            "accession": ACCESSION2,
            "size": DECRYPTED_SIZE,
            "sha256_hash": DECRYPTED_SHA256,
            "storage_alias": "test-node-2",
        },
    ]

    # update dataset to include file 3
    caplog.clear()
    with caplog.at_level(level=logging.INFO, logger="dins.core.information_service"):
        await joint_fixture.kafka.publish_event(
            payload=UPDATE_DATASET_PAYLOAD.model_dump(),
            type_=joint_fixture.config.dataset_upsertion_type,
            topic=joint_fixture.config.dataset_change_topic,
        )
        await joint_fixture.event_subscriber.run(forever=False)
        assert len(caplog.messages) == 0

    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == 200

    dataset_information = response.json()
    assert dataset_information["accession"] == dataset_accession
    assert dataset_information["file_information"] == [
        {
            "accession": ACCESSION1,
            "size": DECRYPTED_SIZE,
            "sha256_hash": DECRYPTED_SHA256,
            "storage_alias": "test-node",
        },
        {
            "accession": ACCESSION2,
            "size": DECRYPTED_SIZE,
            "sha256_hash": DECRYPTED_SHA256,
            "storage_alias": "test-node-2",
        },
        {
            "accession": ACCESSION3,
            "size": DECRYPTED_SIZE,
            "sha256_hash": DECRYPTED_SHA256,
            "storage_alias": "test-node-3",
        },
    ]

    # delete file information - use file_id (UUID), not accession
    for file_id in (FILE_ID_1, FILE_ID_2, FILE_ID_3):
        deletion_requested = models.FileDeletionRequested(file_id=file_id)

        await joint_fixture.kafka.publish_event(
            payload=deletion_requested.model_dump(),
            type_=joint_fixture.config.file_deletion_request_type,
            topic=joint_fixture.config.file_deletion_request_topic,
        )
        await joint_fixture.event_subscriber.run(forever=False)

    # check endpoint response again
    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == 200

    dataset_information = response.json()
    assert dataset_information["accession"] == dataset_accession
    assert dataset_information["file_information"] == [
        {"accession": ACCESSION1},
        {"accession": ACCESSION2},
        {"accession": ACCESSION3},
    ]

    # delete dataset
    deletion_requested = event_schemas.MetadataDatasetID(accession=dataset_accession)

    await joint_fixture.kafka.publish_event(
        payload=deletion_requested.model_dump(),
        type_=joint_fixture.config.dataset_deletion_type,
        topic=joint_fixture.config.dataset_change_topic,
    )
    await joint_fixture.event_subscriber.run(forever=False)

    # check endpoint response for a final time
    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == 404


async def test_accession_map_unique_file_id_index(joint_fixture: JointFixture):
    """Verifies that the unique index on 'file_id' in the accession map collection works.

    Two different accessions must not be mapped to the same file_id. The second
    event should fail due to the unique index and be sent to the DLQ.
    """
    # Publish and consume the first accession map event - should succeed
    await joint_fixture.kafka.publish_event(
        payload=ACCESSION_MAP_1.model_dump(),
        type_="upserted",
        topic=joint_fixture.config.accession_map_topic,
        key=ACCESSION1,
    )
    await joint_fixture.event_subscriber.run(forever=False)

    # Publish a second accession map with the same file_id but a different accession.
    # The unique index on file_id should reject the insert and route the event to the DLQ.
    duplicate_file_id_map = make_accession_map(accession=ACCESSION2, file_id=FILE_ID_1)
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.kafka_dlq_topic
    ) as recorder:
        await joint_fixture.kafka.publish_event(
            payload=duplicate_file_id_map.model_dump(),
            type_="upserted",
            topic=joint_fixture.config.accession_map_topic,
            key=ACCESSION2,
        )
        await joint_fixture.event_subscriber.run(forever=False)

    assert len(recorder.recorded_events) == 1


async def test_accession_map_deletion_event(joint_fixture: JointFixture):
    """Check that the accession map outbox subscriber will process a deletion event."""
    accession_map_dao = await get_file_accession_map_dao(
        dao_factory=joint_fixture.mongodb.dao_factory
    )

    # Store an accession map via outbox upserted event
    await joint_fixture.kafka.publish_event(
        payload=ACCESSION_MAP_1.model_dump(),
        type_="upserted",
        topic=joint_fixture.config.accession_map_topic,
        key=ACCESSION1,
    )
    await joint_fixture.event_subscriber.run(forever=False)

    stored_map = await accession_map_dao.get_by_id(ACCESSION1)
    assert stored_map == ACCESSION_MAP_1

    # Delete it via outbox deleted event
    await joint_fixture.kafka.publish_event(
        payload={},
        type_="deleted",
        topic=joint_fixture.config.accession_map_topic,
        key=ACCESSION1,
    )
    await joint_fixture.event_subscriber.run(forever=False)

    with pytest.raises(ResourceNotFoundError):
        await accession_map_dao.get_by_id(ACCESSION1)
