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

FILE_ID_1 = "test-file"
FILE_ID_2 = "test-file-2"
FILE_ID_3 = "test-file-3"
CHANGED_TYPE = "upserted"
DECRYPTED_SHA256 = "fake-checksum"
DECRYPTED_SIZE = 12345678


FILE_1 = event_schemas.MetadataDatasetFile(
    accession=FILE_ID_1, description="Test File", file_extension=".zip"
)
FILE_2 = event_schemas.MetadataDatasetFile(
    accession=FILE_ID_2, description="Test File", file_extension=".zip"
)
FILE_3 = event_schemas.MetadataDatasetFile(
    accession=FILE_ID_3, description="Test File", file_extension=".zip"
)


INCOMING_DATASET_PAYLOAD = event_schemas.MetadataDatasetOverview(
    accession="test-dataset",
    description="Test dataset",
    title="Dataset for testing",
    stage=event_schemas.MetadataDatasetStage.UPLOAD,
    files=[FILE_1, FILE_2],
)

UPDATE_DATASET_PAYLOAD = INCOMING_DATASET_PAYLOAD.model_copy(
    update={"files": [FILE_1, FILE_2, FILE_3]}
)


INCOMING_FILE_PAYLOAD = event_schemas.FileInternallyRegistered(
    s3_endpoint_alias="test-node",
    file_id=FILE_ID_1,
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

INCOMING_FILE_PAYLOAD_2 = INCOMING_FILE_PAYLOAD.model_copy(
    update={"file_id": FILE_ID_2, "s3_endpoint_alias": "test-node-2"}
)
INCOMING_FILE_PAYLOAD_3 = INCOMING_FILE_PAYLOAD.model_copy(
    update={"file_id": FILE_ID_3, "s3_endpoint_alias": "test-node-3"}
)

FILE_INFORMATION = models.FileInformation(
    accession=FILE_ID_1,
    sha256_hash=DECRYPTED_SHA256,
    size=DECRYPTED_SIZE,
    storage_alias="test-node",
)

pytestmark = pytest.mark.asyncio()


async def test_file_information_journey(
    joint_fixture: JointFixture,  # noqa: F811
    caplog,
):
    """Simulates a typical file information API journey."""
    # Test population path
    file_id = INCOMING_FILE_PAYLOAD.file_id

    await joint_fixture.kafka.publish_event(
        payload=INCOMING_FILE_PAYLOAD.model_dump(),
        type_=joint_fixture.config.file_registered_event_type,
        topic=joint_fixture.config.file_registered_event_topic,
    )
    await joint_fixture.event_subscriber.run(forever=False)

    file_information = await joint_fixture.file_information_dao.get_by_id(file_id)
    assert file_information == FILE_INFORMATION

    # Test reregistration of identical content
    expected_message = f"Found existing information for file {file_id}."

    caplog.clear()
    with caplog.at_level(level=logging.DEBUG, logger="dins.core.information_service"):
        await joint_fixture.kafka.publish_event(
            payload=INCOMING_FILE_PAYLOAD.model_dump(),
            type_=joint_fixture.config.file_registered_event_type,
            topic=joint_fixture.config.file_registered_event_topic,
        )
        await joint_fixture.event_subscriber.run(forever=False)
        assert len(caplog.messages) == 1
        assert expected_message in caplog.messages

    # Test reregistration of mismatching content
    mismatch_message = f"Mismatching information for the file with ID {file_id} has already been registered."
    mismatch_mock = INCOMING_FILE_PAYLOAD.model_copy(
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
    assert models.FileInformation(**response.json()) == FILE_INFORMATION

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


async def test_dataset_information_journey(
    joint_fixture: JointFixture,  # noqa: F811
    caplog,
):
    """Simulates a typical dataset information API journey."""
    # register dataset and verify
    await joint_fixture.kafka.publish_event(
        payload=INCOMING_DATASET_PAYLOAD.model_dump(),
        type_=joint_fixture.config.dataset_upsertion_event_type,
        topic=joint_fixture.config.dataset_event_topic,
    )
    await joint_fixture.event_subscriber.run(forever=False)

    dataset_accession = INCOMING_DATASET_PAYLOAD.accession
    dataset = await joint_fixture.dataset_information_dao.get_by_id(dataset_accession)
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
        {"accession": FILE_ID_1},
        {"accession": FILE_ID_2},
    ]

    # register actual file information
    for file_payload in (
        INCOMING_FILE_PAYLOAD,
        INCOMING_FILE_PAYLOAD_2,
        INCOMING_FILE_PAYLOAD_3,
    ):
        await joint_fixture.kafka.publish_event(
            payload=file_payload.model_dump(),
            type_=joint_fixture.config.file_registered_event_type,
            topic=joint_fixture.config.file_registered_event_topic,
        )
        await joint_fixture.event_subscriber.run(forever=False)

    # check again to verify that correct file information is returned now
    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == 200

    dataset_information = response.json()
    assert dataset_information["accession"] == dataset_accession
    assert dataset_information["file_information"] == [
        {
            "accession": FILE_ID_1,
            "size": DECRYPTED_SIZE,
            "sha256_hash": DECRYPTED_SHA256,
            "storage_alias": "test-node",
        },
        {
            "accession": FILE_ID_2,
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
            type_=joint_fixture.config.dataset_upsertion_event_type,
            topic=joint_fixture.config.dataset_event_topic,
        )
        await joint_fixture.event_subscriber.run(forever=False)
        assert len(caplog.messages) == 0

    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == 200

    dataset_information = response.json()
    assert dataset_information["accession"] == dataset_accession
    assert dataset_information["file_information"] == [
        {
            "accession": FILE_ID_1,
            "size": DECRYPTED_SIZE,
            "sha256_hash": DECRYPTED_SHA256,
            "storage_alias": "test-node",
        },
        {
            "accession": FILE_ID_2,
            "size": DECRYPTED_SIZE,
            "sha256_hash": DECRYPTED_SHA256,
            "storage_alias": "test-node-2",
        },
        {
            "accession": FILE_ID_3,
            "size": DECRYPTED_SIZE,
            "sha256_hash": DECRYPTED_SHA256,
            "storage_alias": "test-node-3",
        },
    ]

    # delete file information
    for file_id in (FILE_ID_1, FILE_ID_2, FILE_ID_3):
        deletion_requested = event_schemas.FileDeletionRequested(file_id=file_id)

        await joint_fixture.kafka.publish_event(
            payload=deletion_requested.model_dump(),
            type_=CHANGED_TYPE,
            topic=joint_fixture.config.files_to_delete_topic,
        )
        await joint_fixture.outbox_subscriber.run(forever=False)

    # check endpoint response again
    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == 200

    dataset_information = response.json()
    assert dataset_information["accession"] == dataset_accession
    assert dataset_information["file_information"] == [
        {"accession": FILE_ID_1},
        {"accession": FILE_ID_2},
        {"accession": FILE_ID_3},
    ]

    # delete dataset
    deletion_requested = event_schemas.MetadataDatasetID(accession=dataset_accession)

    await joint_fixture.kafka.publish_event(
        payload=deletion_requested.model_dump(),
        type_=joint_fixture.config.dataset_deletion_event_type,
        topic=joint_fixture.config.dataset_event_topic,
    )
    await joint_fixture.event_subscriber.run(forever=False)

    # check endpoint response for a final time
    response = await joint_fixture.rest_client.get(url)
    assert response.status_code == 404
