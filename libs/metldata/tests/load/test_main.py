# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the main modules."""

import json
from copy import deepcopy

import pytest
from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.protocols.dao import ResourceNotFoundError
from hexkit.providers.akafka.testutils import (  # noqa: F401; pylint: disable=unused-import
    KafkaFixture,
    kafka_fixture,
)

from metldata.artifacts_rest.artifact_dao import ArtifactDaoCollection
from metldata.artifacts_rest.load_resources import (
    convert_file_information,
    get_file_slots,
)
from metldata.artifacts_rest.models import ArtifactResource, GlobalStats
from metldata.load.auth import generate_token
from metldata.load.stats import STATS_COLLECTION_NAME
from tests.fixtures.load.joint import (  # noqa: F401; pylint: disable=unused-import
    EMBEDDED_DATASET_TEST_PATH,
    JointFixture,
    joint_fixture,
)
from tests.fixtures.mongodb import (  # noqa: F401; pylint: disable=unused-import
    MongoDbFixture,
    mongodb_fixture,
)
from tests.fixtures.workflows import EXAMPLE_ARTIFACTS


@pytest.mark.asyncio
async def test_load_artifacts_endpoint_happy(
    joint_fixture: JointFixture,  # noqa: F811
):
    """Test the happy path of using the load artifacts endpoint."""

    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.dataset_change_event_topic
    ) as dataset_recorder:
        async with joint_fixture.kafka.record_events(
            in_topic=joint_fixture.config.resource_change_event_topic
        ) as resource_recorder:
            response = await joint_fixture.client.post(
                "/rpc/load-artifacts",
                json=joint_fixture.artifact_resources,
                headers={"Authorization": f"Bearer {joint_fixture.token}"},
            )
            assert response.status_code == 204

    assert len(resource_recorder.recorded_events) == 2
    for event in resource_recorder.recorded_events:
        assert event.type_ == joint_fixture.config.resource_upsertion_type
    assert len(dataset_recorder.recorded_events) == 2
    for event in dataset_recorder.recorded_events:
        assert event.type_ == joint_fixture.config.dataset_upsertion_type

    # check that the artifact resources were loaded based on an example:
    expected_artifact_name = "embedded_public"

    expected_file_resource_class = "StudyFile"
    expected_file_resource_id = joint_fixture.expected_file_resource_content[
        "accession"
    ]

    expected_embedded_dataset_resource_class = "EmbeddedDataset"
    expected_embedded_dataset_resource_id = (
        joint_fixture.expected_embedded_dataset_resource_content["accession"]
    )

    dao_collection = await ArtifactDaoCollection.construct(
        dao_factory=joint_fixture.mongodb.dao_factory,
        artifact_infos=joint_fixture.artifact_infos,
    )

    dao = await dao_collection.get_dao(
        artifact_name=expected_artifact_name, class_name=expected_file_resource_class
    )
    observed_resource = await dao.get_by_id(expected_file_resource_id)
    assert observed_resource.content == joint_fixture.expected_file_resource_content

    dao = await dao_collection.get_dao(
        artifact_name=expected_artifact_name,
        class_name=expected_embedded_dataset_resource_class,
    )
    observed_resource = await dao.get_by_id(expected_embedded_dataset_resource_id)
    assert (
        observed_resource.content
        == joint_fixture.expected_embedded_dataset_resource_content
    )

    # check that the summary statistics has been created:
    expected_resource_stats = {
        "DataAccessPolicy": {"count": 1},
        "Dataset": {"count": 2},
        "DataAccessCommittee": {"count": 1},
        "StudyFile": {
            "count": 3,
            "stats": {"format": [{"value": "FASTQ", "count": 3}]},
        },
        "Study": {"count": 1},
        "EmbeddedDataset": {"count": 2},
    }
    stats_dao = await joint_fixture.mongodb.dao_factory.get_dao(
        name=STATS_COLLECTION_NAME, dto_model=GlobalStats, id_field="id"
    )
    async for stats in stats_dao.find_all(mapping={}):
        assert stats.id == "global"
        assert abs((now_as_utc() - stats.created).seconds) < 5
        assert stats.resource_stats == expected_resource_stats

    # replace tested resource with slightly changed one
    changed_accession = "CHANGED_EMBEDDED_DATASET"
    new_artifact_resources = deepcopy(joint_fixture.artifact_resources)
    del new_artifact_resources[expected_artifact_name][0]["embedded_dataset"][0]
    new_artifact_resources[expected_artifact_name][0]["embedded_dataset"][0][
        "accession"
    ] = "CHANGED_EMBEDDED_DATASET"
    expected_resource_content = new_artifact_resources[expected_artifact_name][0][
        "embedded_dataset"
    ][0]

    # submit changed request
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.dataset_change_event_topic
    ) as dataset_recorder:
        async with joint_fixture.kafka.record_events(
            in_topic=joint_fixture.config.resource_change_event_topic
        ) as resource_recorder:
            response = await joint_fixture.client.post(
                "/rpc/load-artifacts",
                json=new_artifact_resources,
                headers={"Authorization": f"Bearer {joint_fixture.token}"},
            )
            assert response.status_code == 204

    assert len(resource_recorder.recorded_events) == 3
    for event in resource_recorder.recorded_events:
        if event.key == f"dataset_embedded_{changed_accession}":
            assert event.type_ == joint_fixture.config.resource_upsertion_type
        else:
            assert event.type_ == joint_fixture.config.resource_deletion_event_type

    assert len(dataset_recorder.recorded_events) == 3

    for event in dataset_recorder.recorded_events:
        if event.key == f"dataset_embedded_{changed_accession}":
            assert event.type_ == joint_fixture.config.dataset_upsertion_type
        else:
            assert event.type_ == joint_fixture.config.dataset_deletion_type

    observed_resource = await dao.get_by_id(changed_accession)
    assert observed_resource.content == expected_resource_content

    # submit an empty request:
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.dataset_change_event_topic
    ) as dataset_recorder:
        async with joint_fixture.kafka.record_events(
            in_topic=joint_fixture.config.resource_change_event_topic
        ) as resource_recorder:
            response = await joint_fixture.client.post(
                "/rpc/load-artifacts",
                json={},
                headers={"Authorization": f"Bearer {joint_fixture.token}"},
            )
            assert response.status_code == 204

    assert len(resource_recorder.recorded_events) == 9
    for event in resource_recorder.recorded_events:
        assert event.type_ == joint_fixture.config.resource_deletion_event_type

    assert len(dataset_recorder.recorded_events) == 1
    for event in dataset_recorder.recorded_events:
        assert event.type_ == joint_fixture.config.dataset_deletion_type

    # confirm that example resource was deleted:
    with pytest.raises(ResourceNotFoundError):
        await dao.get_by_id(changed_accession)


@pytest.mark.asyncio
async def test_load_artifacts_endpoint_invalid_resources(
    joint_fixture: JointFixture,  # noqa: F811
):
    """Test using the load artifacts endpoint with resources of unknown artifacts."""

    # load example artifacts resources:
    unknown_artifact_resources = {
        "unknown_artifact": [list(EXAMPLE_ARTIFACTS.values())[0]]
    }
    response = await joint_fixture.client.post(
        "/rpc/load-artifacts",
        json=unknown_artifact_resources,
        headers={"Authorization": f"Bearer {joint_fixture.token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_load_artifacts_endpoint_invalid_token(
    joint_fixture: JointFixture,  # noqa: F811
):
    """Test that using the load artifacts endpoint with an invalid token fails."""

    invalid_token = generate_token()

    # load artifact resources with invalid token:
    response = await joint_fixture.client.post(
        "/rpc/load-artifacts",
        json={},
        headers={"Authorization": f"Bearer {invalid_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_file_slot_transformation(
    joint_fixture: JointFixture,  # noqa: F811
):
    """Test that file slots are discovered and file extensions are extracted correctly"""

    with open(EMBEDDED_DATASET_TEST_PATH, "r", encoding="utf-8") as file:
        embedded_datasets = json.load(file)

    file_slots = []
    artifact_info = joint_fixture.artifact_infos[0]

    # get all embedded datset resources
    for embedded_dataset in embedded_datasets["embedded_dataset"]:
        resource = ArtifactResource(
            id_=embedded_dataset["accession"],
            class_name="EmbeddedDataset",
            content=embedded_dataset,
        )
        current_file_slots = get_file_slots(
            artifact_info=artifact_info, resource=resource
        )
        file_slots.extend(current_file_slots)

    extension_mapping = {
        "STUDY_FILE_1": ".fastq.gz",
        "STUDY_FILE_2": ".fastq",
        "STUDY_FILE_3": ".gz",
        "STUDY_FILE_4": "",
    }
    for file_info in convert_file_information(file_slots=file_slots):
        assert extension_mapping[file_info.accession] == file_info.file_extension
