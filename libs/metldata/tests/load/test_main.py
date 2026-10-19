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
#

"""Test the main modules."""

import json
from copy import deepcopy

import pytest

from ghga_service_commons.utils.utc_dates import now_as_utc
from hexkit.protocols.dao import ResourceNotFoundError
from metldata.artifacts_rest.artifact_dao import ArtifactDaoCollection
from metldata.artifacts_rest.load_resources import (
    convert_file_information,
    get_file_slots,
)
from metldata.artifacts_rest.models import ArtifactResource, GlobalStats
from metldata.load.api import FILE_GOVERNANCE_COLLECTION_NAME
from metldata.load.auth import generate_token
from metldata.load.load import resolve_governance_records
from metldata.load.models import FileGovernanceRecord
from metldata.load.stats import STATS_COLLECTION_NAME
from tests.fixtures.load.joint import (
    EMBEDDED_DATASET_TEST_PATH,
    JointFixture,
    joint_fixture,  # noqa: F401
)
from tests.fixtures.workflows import EXAMPLE_ARTIFACTS

pytestmark = pytest.mark.asyncio()


async def test_load_artifacts_endpoint_happy(joint_fixture: JointFixture):  # noqa: F811
    """Test the happy path of using the load artifacts endpoint."""
    resources = joint_fixture.artifact_resources
    async with (
        joint_fixture.kafka.record_events(
            in_topic=joint_fixture.config.dataset_change_topic
        ) as dataset_recorder,
        joint_fixture.kafka.record_events(
            in_topic=joint_fixture.config.resource_change_topic
        ) as resource_recorder,
    ):
        response = await joint_fixture.client.post(
            "/rpc/load-artifacts",
            json=resources,
            headers={"Authorization": f"Bearer {joint_fixture.token}"},
        )
        assert response.status_code == 204

    # check that the recorded events match what we expect from the resources:
    datasets = resources["embedded_public"][0]["content"]["embedded_dataset"]
    for event in resource_recorder.recorded_events:
        assert event.type_ == joint_fixture.config.resource_upsertion_type
    assert len(resource_recorder.recorded_events) == len(datasets) == 2
    assert len(dataset_recorder.recorded_events) == len(datasets) == 2
    for event, dataset in zip(dataset_recorder.recorded_events, datasets, strict=True):
        assert event.type_ == joint_fixture.config.dataset_upsertion_type
        payload = event.payload
        assert payload["title"] == dataset["title"]
        assert payload["description"] == dataset["description"]
        assert payload["dac_alias"] == "DAC_1"
        assert payload["dac_email"] == "dac1@institute.org"

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

    # check that the governance of every added_accessions file was stored:
    stored_records = _stored_governance_records(joint_fixture)
    expected_records = {
        record.file_accession: record
        for record in resolve_governance_records(
            artifact_resources=resources,
            governance_artifact_name=joint_fixture.config.governance_artifact_name,
        )
    }
    assert len(stored_records) == len(
        _file_accessions(resources["added_accessions"][0])
    )
    assert stored_records == expected_records

    # check that the summary statistics has been created:
    expected_resource_stats = {
        "StudyFile": {
            "count": 3,
            "stats": {"format": [{"value": "FASTQ", "count": 3}]},
        },
        "Study": {"count": 1},
        "Analysis": {"count": 0},
        "AnalysisProcess": {"count": 0},
        "Biospecimen": {"count": 0},
        "SequencingExperiment": {"count": 0},
        "SampleFile": {"count": 0},
        "Condition": {"count": 0},
        "SequencingProtocol": {"count": 0},
        "Sample": {"count": 0},
        "SequencingProcessFile": {"count": 0},
        "Dataset": {"count": 2},
        "AnalysisProcessOutputFile": {"count": 0},
        "SequencingProcess": {"count": 0},
        "Publication": {"count": 0},
        "DataAccessPolicy": {"count": 1},
        "Individual": {"count": 0},
        "Trio": {"count": 0},
        "DataAccessCommittee": {"count": 1},
        "LibraryPreparationProtocol": {"count": 0},
        "EmbeddedDataset": {"count": 2},
    }
    stats_dao = await joint_fixture.mongodb.dao_factory.get_dao(
        name=STATS_COLLECTION_NAME, dto_model=GlobalStats, id_field="id"
    )
    async for stats in stats_dao.find_all(mapping={}):
        assert stats.id == "global"
        assert abs((now_as_utc() - stats.created).seconds) < 5
        assert stats.resource_stats == expected_resource_stats

    # Delete first dataset and replace the remaining one with a changed one
    # This should result in two deletion events and one upsertion event
    changed_accession = "CHANGED_EMBEDDED_DATASET"
    new_artifact_resources = deepcopy(joint_fixture.artifact_resources)
    del new_artifact_resources[expected_artifact_name][0]["content"][
        "embedded_dataset"
    ][0]
    new_artifact_resources[expected_artifact_name][0]["content"]["embedded_dataset"][0][
        "accession"
    ] = "CHANGED_EMBEDDED_DATASET"
    expected_resource_content = new_artifact_resources[expected_artifact_name][0][
        "content"
    ]["embedded_dataset"][0]

    # submit changed request
    async with (
        joint_fixture.kafka.record_events(
            in_topic=joint_fixture.config.dataset_change_topic
        ) as dataset_recorder,
        joint_fixture.kafka.record_events(
            in_topic=joint_fixture.config.resource_change_topic
        ) as resource_recorder,
    ):
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
            assert event.type_ == joint_fixture.config.resource_deletion_type

    assert len(dataset_recorder.recorded_events) == 3

    for event in dataset_recorder.recorded_events:
        if event.key == f"dataset_embedded_{changed_accession}":
            assert event.type_ == joint_fixture.config.dataset_upsertion_type
        else:
            assert event.type_ == joint_fixture.config.dataset_deletion_type

    observed_resource = await dao.get_by_id(changed_accession)
    assert observed_resource.content == expected_resource_content

    # submit an empty request:
    async with (
        joint_fixture.kafka.record_events(
            in_topic=joint_fixture.config.dataset_change_topic
        ) as dataset_recorder,
        joint_fixture.kafka.record_events(
            in_topic=joint_fixture.config.resource_change_topic
        ) as resource_recorder,
    ):
        response = await joint_fixture.client.post(
            "/rpc/load-artifacts",
            json={},
            headers={"Authorization": f"Bearer {joint_fixture.token}"},
        )
        assert response.status_code == 204

    # Check for one deletion event for each topic (the first 2 datasets were deleted earlier)
    assert len(resource_recorder.recorded_events) == 1
    for event in resource_recorder.recorded_events:
        assert event.type_ == joint_fixture.config.resource_deletion_type

    assert len(dataset_recorder.recorded_events) == 1
    for event in dataset_recorder.recorded_events:
        assert event.type_ == joint_fixture.config.dataset_deletion_type

    # confirm that example resource was deleted:
    with pytest.raises(ResourceNotFoundError):
        await dao.get_by_id(changed_accession)


async def test_load_stats_public(joint_fixture: JointFixture):  # noqa: F811
    """Verify that we can load the stats_public artifact into the load api.

    Also checks that we publish neither upsertion nor deletion events for stats_public.
    """
    artifacts_to_load = deepcopy(joint_fixture.artifact_resources)

    # Remove artifacts that are not relevant for this test
    artifacts_to_load.pop("added_accessions", None)
    artifacts_to_load.pop("embedded_public", None)

    # Double-check that the database is empty before we start
    db = joint_fixture.mongodb.client[joint_fixture.config.db_name]
    stats_collection = db["art_stats_public_class_DatasetStats"]
    assert not stats_collection.find().to_list()

    expected_doc_count = 2  # There are two resources in the stats_public artifact
    change_topic = joint_fixture.config.resource_change_topic

    # Insert the stats_public artifact and check for upsertion events (expect 0)
    async with joint_fixture.kafka.record_events(in_topic=change_topic) as recorder:
        response = await joint_fixture.client.post(
            "/rpc/load-artifacts",
            json=artifacts_to_load,
            headers={"Authorization": f"Bearer {joint_fixture.token}"},
        )
        assert response.status_code == 204

    # Check the DB -- the two stats_public artifact resources should have been saved
    assert len(stats_collection.find().to_list()) == expected_doc_count

    # Delete the stats_public artifact and check for deletion events (expect 0)
    async with joint_fixture.kafka.record_events(in_topic=change_topic) as recorder:
        response = await joint_fixture.client.post(
            "/rpc/load-artifacts",
            json={},
            headers={"Authorization": f"Bearer {joint_fixture.token}"},
        )
        assert response.status_code == 204
    assert not recorder.recorded_events

    # Check the DB -- the stats_public artifact resources should have been deleted
    assert stats_collection.find().to_list() == []


async def test_whole_artifact_loading(joint_fixture: JointFixture):  # noqa: F811
    """Test the loading of whole artifacts. This covers initial load, modification,
    re-submission without change, and deletion.
    """
    # 1. Make a copy of the test data because we're going to modify it
    artifacts_to_load = deepcopy(joint_fixture.artifact_resources)
    test_artifact = artifacts_to_load["added_accessions"][0]

    # Verify that the test data isn't already in the database
    db = joint_fixture.mongodb.client[joint_fixture.config.db_name]
    test_collection = db["added_accessions"]
    assert not test_collection.find().to_list()

    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.artifact_topic
    ) as artifact_recorder:
        response = await joint_fixture.client.post(
            "/rpc/load-artifacts",
            json=artifacts_to_load,
            headers={"Authorization": f"Bearer {joint_fixture.token}"},
        )
        assert response.status_code == 204

    # Make sure the added_accessions artifact was published as an event is in the DB
    docs = test_collection.find().to_list()
    assert len(docs) == 1
    assert docs[0]["artifact_name"] == "added_accessions"
    assert docs[0]["_id"] == test_artifact["study_accession"]
    assert docs[0]["content"] == test_artifact["content"]

    assert len(artifact_recorder.recorded_events) == 1
    artifact_event = artifact_recorder.recorded_events[0]
    assert artifact_event.type_ == "upserted"
    test_artifact_study_accession = artifacts_to_load["added_accessions"][0][
        "study_accession"
    ]
    assert artifact_event.key == f"added_accessions:{test_artifact_study_accession}"
    assert artifact_event.payload == artifacts_to_load["added_accessions"][0]

    # 2. Load same data again without changes
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.artifact_topic
    ) as artifact_recorder2:
        response = await joint_fixture.client.post(
            "/rpc/load-artifacts",
            json=artifacts_to_load,
            headers={"Authorization": f"Bearer {joint_fixture.token}"},
        )
        assert response.status_code == 204

    # Make sure no event was published when the event was unchanged
    assert not artifact_recorder2.recorded_events

    # 3. Modify the artifact and load again
    test_artifact["content"]["samples"].clear()
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.artifact_topic
    ) as artifact_recorder3:
        response = await joint_fixture.client.post(
            "/rpc/load-artifacts",
            json=artifacts_to_load,
            headers={"Authorization": f"Bearer {joint_fixture.token}"},
        )
        assert response.status_code == 204

    # Make sure the updated artifact was published as an event
    assert len(artifact_recorder3.recorded_events) == 1
    artifact_event = artifact_recorder3.recorded_events[0]
    assert artifact_event.type_ == "upserted"
    assert artifact_event.key == f"added_accessions:{test_artifact_study_accession}"
    assert artifact_event.payload == test_artifact

    # Make sure the artifact was updated in the database
    docs = test_collection.find().to_list()
    assert len(docs) == 1
    assert docs[0]["content"]["samples"] == []  # The samples list should be empty

    # 4. Delete all artifacts
    async with joint_fixture.kafka.record_events(
        in_topic=joint_fixture.config.artifact_topic
    ) as artifact_recorder4:
        response = await joint_fixture.client.post(
            "/rpc/load-artifacts",
            json={},
            headers={"Authorization": f"Bearer {joint_fixture.token}"},
        )
        assert response.status_code == 204

    # Make sure the artifact deletion was published as an event
    assert len(artifact_recorder4.recorded_events) == 1
    artifact_event = artifact_recorder4.recorded_events[0]
    assert artifact_event.type_ == "deleted"
    assert artifact_event.key == f"added_accessions:{test_artifact_study_accession}"
    assert artifact_event.payload == {
        "artifact_name": "added_accessions",
        "study_accession": test_artifact_study_accession,
    }

    # Make sure the artifact was deleted from the database
    assert not test_collection.find().to_list()


async def test_load_artifacts_endpoint_invalid_resources(
    joint_fixture: JointFixture,  # noqa: F811
):
    """Test using the load artifacts endpoint with resources of unknown artifacts."""
    # load example artifacts resources:
    unknown_artifact_resources = {
        "unknown_artifact": [list(EXAMPLE_ARTIFACTS.values())[0]]  # noqa: RUF015
    }
    response = await joint_fixture.client.post(
        "/rpc/load-artifacts",
        json=unknown_artifact_resources,
        headers={"Authorization": f"Bearer {joint_fixture.token}"},
    )
    assert response.status_code == 422


def _add_second_study(artifact: dict) -> None:
    """Make the artifact hold a second study."""
    artifact["content"]["studies"].append({"accession": "GHGAS_OTHER"})


def _send_other_study_accession(artifact: dict) -> None:
    """Make the artifact be sent with the accession of a study it does not hold."""
    artifact["study_accession"] = "GHGAS_OTHER"


@pytest.mark.parametrize(
    "break_artifact, expected_detail",
    [
        (_add_second_study, "Expected exactly one study, found 2"),
        (_send_other_study_accession, "was sent with study accession 'GHGAS_OTHER'"),
    ],
    ids=["two_studies", "mismatched_study_accession"],
)
async def test_load_artifacts_endpoint_invalid_publishable_artifact(
    joint_fixture: JointFixture,  # noqa: F811
    break_artifact,
    expected_detail: str,
):
    """Test that a publishable artifact that does not hold exactly one study, matching
    the study accession it is sent with, is rejected and nothing is stored.
    """
    artifacts_to_load = deepcopy(joint_fixture.artifact_resources)
    break_artifact(artifacts_to_load["added_accessions"][0])

    response = await joint_fixture.client.post(
        "/rpc/load-artifacts",
        json=artifacts_to_load,
        headers={"Authorization": f"Bearer {joint_fixture.token}"},
    )

    assert response.status_code == 422
    assert expected_detail in response.json()["detail"]
    db = joint_fixture.mongodb.client[joint_fixture.config.db_name]
    assert not db["added_accessions"].find().to_list()


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
    assert response.status_code == 401


async def test_file_slot_transformation(joint_fixture: JointFixture):  # noqa: F811
    """Test that file slots are discovered and file extensions are extracted correctly"""
    with open(EMBEDDED_DATASET_TEST_PATH, encoding="utf-8") as file:
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


def _stored_governance_records(
    joint_fixture: JointFixture,  # noqa: F811
) -> dict[str, FileGovernanceRecord]:
    """Return the stored governance records by file accession."""
    governance_collection = joint_fixture.mongodb.client[joint_fixture.config.db_name][
        FILE_GOVERNANCE_COLLECTION_NAME
    ]
    stored_records = {}
    for doc in governance_collection.find().to_list():
        file_accession = doc.pop("_id")
        stored_records[file_accession] = FileGovernanceRecord(
            file_accession=file_accession, **doc
        )
    return stored_records


def _file_accessions(artifact: dict) -> set[str]:
    """Return the accessions of all files in an artifact."""
    return {
        file["accession"]
        for class_slot, resources in artifact["content"].items()
        if class_slot.endswith("_files")
        for file in resources
    }


def _copy_with_new_accessions(artifact: dict, *, prefix: str) -> dict:
    """Copy an artifact as another study by prefixing every accession in it."""
    accessions = {
        resource["accession"]
        for resources in artifact["content"].values()
        for resource in resources
        if "accession" in resource
    }

    def prefixed(value):
        if isinstance(value, str) and value in accessions:
            return f"{prefix}{value}"
        if isinstance(value, list):
            return [prefixed(item) for item in value]
        if isinstance(value, dict):
            return {key: prefixed(item) for key, item in value.items()}
        return value

    return {
        **prefixed(artifact),
        "study_accession": prefixed(artifact["study_accession"]),
    }


async def test_governance_records_follow_full_state(
    joint_fixture: JointFixture,  # noqa: F811
):
    """Test that a load which drops a study deletes the governance records of its
    files and keeps those of the remaining study.
    """
    artifacts_to_load = deepcopy(joint_fixture.artifact_resources)
    first_study = artifacts_to_load["added_accessions"][0]
    second_study = _copy_with_new_accessions(first_study, prefix="SECOND_")
    artifacts_to_load["added_accessions"].append(second_study)
    governance_collection = joint_fixture.mongodb.client[joint_fixture.config.db_name][
        FILE_GOVERNANCE_COLLECTION_NAME
    ]

    response = await joint_fixture.client.post(
        "/rpc/load-artifacts",
        json=artifacts_to_load,
        headers={"Authorization": f"Bearer {joint_fixture.token}"},
    )
    assert response.status_code == 204
    stored_file_accessions = {
        doc["_id"] for doc in governance_collection.find().to_list()
    }
    assert stored_file_accessions == _file_accessions(first_study) | _file_accessions(
        second_study
    )

    artifacts_to_load["added_accessions"] = [second_study]
    response = await joint_fixture.client.post(
        "/rpc/load-artifacts",
        json=artifacts_to_load,
        headers={"Authorization": f"Bearer {joint_fixture.token}"},
    )
    assert response.status_code == 204
    stored_file_accessions = {
        doc["_id"] for doc in governance_collection.find().to_list()
    }
    assert stored_file_accessions == _file_accessions(second_study)


def _dangle_data_access_policies(artifacts: dict) -> None:
    """Point every dataset to a data access policy that does not exist."""
    for dataset in artifacts["added_accessions"][0]["content"]["datasets"]:
        dataset["data_access_policy"] = "DANGLING"


def _share_file_accession_across_studies(artifacts: dict) -> None:
    """Add a second study whose first file has the accession of a first-study file."""
    first_study = artifacts["added_accessions"][0]
    second_study = _copy_with_new_accessions(first_study, prefix="SECOND_")
    second_study["content"]["research_data_files"][0]["accession"] = first_study[
        "content"
    ]["research_data_files"][0]["accession"]
    artifacts["added_accessions"].append(second_study)


def _reuse_file_of_other_dataset(artifacts: dict) -> None:
    """Make a file reuse a file of another dataset in the same study, so the reused
    accession matches files in two datasets.
    """
    content = artifacts["added_accessions"][0]["content"]
    reused_file = content["research_data_files"][0]
    reusing_file = next(
        file
        for class_slot, resources in content.items()
        if class_slot.endswith("_files")
        for file in resources
        if file["dataset"] != reused_file["dataset"]
    )
    reusing_file["reused_accession"] = reused_file["accession"]


@pytest.mark.parametrize(
    "break_artifacts, expected_detail",
    [
        (_dangle_data_access_policies, "DANGLING"),
        (_share_file_accession_across_studies, "occurs in more than one artifact"),
        (_reuse_file_of_other_dataset, "resolves to 2 datasets"),
    ],
)
async def test_invalid_governance_rejected(
    joint_fixture: JointFixture,  # noqa: F811
    break_artifacts,
    expected_detail: str,
):
    """Test that artifacts whose governance cannot be stored unambiguously return
    422 and nothing is written to the database.
    """
    artifacts_to_load = deepcopy(joint_fixture.artifact_resources)
    break_artifacts(artifacts_to_load)

    response = await joint_fixture.client.post(
        "/rpc/load-artifacts",
        json=artifacts_to_load,
        headers={"Authorization": f"Bearer {joint_fixture.token}"},
    )

    assert response.status_code == 422
    assert expected_detail in response.json()["detail"]
    db = joint_fixture.mongodb.client[joint_fixture.config.db_name]
    for collection_name in db.list_collection_names():
        assert not db[collection_name].find().to_list(), collection_name
