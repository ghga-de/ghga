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

"""Testing the consumer for legacy searchable resource events.

LEGACY: covers the consumer that fetches searchable resources from metldata.
The consumer validates and routes the events and extracts the embedded study
into the study DAO. Remove together with the consumer once this service owns studies
and experimental metadata itself.
"""

from uuid import UUID, uuid4

import pytest
from hexkit.providers.mongokafka import MongoKafkaDaoPublisherFactory

from rs.adapters.outbound.dao import get_file_accession_dao
from rs.constants import FILE_ACCESSION_COLLECTION, STUDY_COLLECTION
from rs.core.legacy_resources import _LEGACY_CREATED_BY
from rs.core.models import FileAccession, StudyStatus
from rs.ports.inbound.registry import RegistryPort
from tests.fixtures.joint import JointFixture

pytestmark = pytest.mark.asyncio


def _study_collection(joint_fixture: JointFixture):
    """Return the MongoDB collection backing the study DAO."""
    db = joint_fixture.mongodb.client[joint_fixture.config.db_name]
    return db[STUDY_COLLECTION]


def _study_count(joint_fixture: JointFixture) -> int:
    """Count the studies currently stored in the study DAO collection."""
    return _study_collection(joint_fixture).count_documents({})


def _file_accession_collection(joint_fixture: JointFixture):
    """Return the MongoDB collection backing the file accession DAO."""
    db = joint_fixture.mongodb.client[joint_fixture.config.db_name]
    return db[FILE_ACCESSION_COLLECTION]


def _embedded_dataset_payload(study_accession: str = "GHGAS1") -> dict:
    """Build a searchable-resource payload embedding a study (as metldata emits).

    The ``files`` key aggregates all file accessions of the resource as a flat list of
    accession strings; that is the only source of tracked file accessions. The
    ``research_data_files`` key (a list of file objects) is included to confirm that
    such per-category lists are *not* consulted.

    The payload deliberately carries properties we do not consume - both at the content
    level (``accession``, ``title``, ``description``, ``research_data_files``) and
    inside the embedded study (``alias``, ``ega_accession``, ``description_html``) -
    to confirm
    that extra properties do not make validation of the consumed subschema fail.
    """
    return {
        "accession": "GHGAD1",
        "class_name": "EmbeddedDataset",
        "content": {
            # Content-level properties we do not consume.
            "accession": "GHGAD1",
            "title": "DS dataset",
            "description": "A dataset embedding a study",
            # Per-category file list - we ignore these in favor of the aggregated list.
            "research_data_files": [
                {"accession": "GHGAF9", "name": "file1.fastq.gz"},
            ],
            # Only the aggregation of all file accessions are tracked.
            "files": ["GHGAF1", "GHGAF2", "GHGAF3", "GHGAF4"],
            # The study is tracked as well.
            "study": {
                "accession": study_accession,
                "title": "A test study",
                "description": "This is a study used for testing",
                "types": ["WHOLE_GENOME_SEQUENCING"],
                "affiliations": ["Some Institute"],
                "datasets": ["GHGAD1"],
                "publications": [],
                # Non-consumed properties below.
                "alias": "TEST_STUDY",
                "ega_accession": "EGAS1",
            },
        },
    }


# The aggregated file accessions carried by the ``files`` key in the payload above.
_PAYLOAD_FILE_ACCESSIONS = {"GHGAF1", "GHGAF2", "GHGAF3", "GHGAF4"}


async def test_searchable_resource_upsertion_stores_study(joint_fixture: JointFixture):
    """An upsertion event extracts the embedded study and stores it in the study DAO."""
    config = joint_fixture.config

    await joint_fixture.kafka.publish_event(
        payload=_embedded_dataset_payload(),
        type_=config.resource_upsertion_type,
        topic=config.resource_change_topic,
        key="dataset_embedded_GHGAD1",
    )
    await joint_fixture.event_subscriber.run(forever=False)

    assert _study_count(joint_fixture) == 1
    stored = _study_collection(joint_fixture).find_one({"_id": "GHGAS1"})
    assert stored is not None
    assert stored["title"] == "A test study"
    assert stored["types"] == ["WHOLE_GENOME_SEQUENCING"]
    assert stored["affiliations"] == ["Some Institute"]
    assert stored["status"] == StudyStatus.ARCHIVED
    assert UUID(str(stored["created_by"])) == _LEGACY_CREATED_BY
    assert stored["num_datasets"] == 1
    assert stored["num_publications"] == 0


async def test_existing_study_is_not_updated(joint_fixture: JointFixture):
    """Re-consuming a known study (e.g. via another embedded dataset) leaves it intact.

    Studies are only created via this mechanism, never updated, so the originally
    stored record - including its ``created`` timestamp - must be preserved even when a
    later event carries changed study content.
    """
    config = joint_fixture.config

    await joint_fixture.kafka.publish_event(
        payload=_embedded_dataset_payload(),
        type_=config.resource_upsertion_type,
        topic=config.resource_change_topic,
        key="dataset_embedded_GHGAD1",
    )
    await joint_fixture.event_subscriber.run(forever=False)
    stored_first = _study_collection(joint_fixture).find_one({"_id": "GHGAS1"})
    assert stored_first is not None

    # A second event carrying the same study id but a different title must not update
    # it.
    changed = _embedded_dataset_payload()
    changed["content"]["study"]["title"] = "A different title"
    await joint_fixture.kafka.publish_event(
        payload=changed,
        type_=config.resource_upsertion_type,
        topic=config.resource_change_topic,
        key="dataset_embedded_GHGAD1",
    )
    await joint_fixture.event_subscriber.run(forever=False)

    assert _study_count(joint_fixture) == 1
    stored_second = _study_collection(joint_fixture).find_one({"_id": "GHGAS1"})
    assert stored_second == stored_first
    assert stored_second["title"] == "A test study"


@pytest.mark.parametrize(
    "content",
    [
        pytest.param({"title": "Some resource"}, id="no_study"),
        pytest.param({"study": None, "files": []}, id="null_study"),
        pytest.param(
            {"study": {"title": "No accession"}, "files": []},
            id="study_without_accession",
        ),
        pytest.param({"study": {"accession": "GHGAS1"}}, id="no_files_list"),
    ],
)
async def test_resource_not_matching_expected_schema_is_ignored(
    joint_fixture: JointFixture, content: dict
):
    """A resource that does not match the expected schema persists nothing.

    The resource must carry content with a non-null study that has an accession plus a
    files list; if any of that is missing, the whole event is ignored (with a warning),
    so neither a study nor any file accessions are stored.
    """
    config = joint_fixture.config

    await joint_fixture.kafka.publish_event(
        payload={
            "accession": "GHGA:RESOURCE1",
            "class_name": "ExperimentMethod",
            "content": content,
        },
        type_=config.resource_upsertion_type,
        topic=config.resource_change_topic,
        key="experiment_method_GHGA:RESOURCE1",
    )
    await joint_fixture.event_subscriber.run(forever=False)

    assert _study_count(joint_fixture) == 0
    assert _file_accession_collection(joint_fixture).count_documents({}) == 0


async def test_upsertion_tracks_file_accessions(joint_fixture: JointFixture):
    """An upsertion event tracks the file accessions found under the ``files`` key.

    Each accession in the aggregated ``files`` list is stored as an unmapped
    FileAccession (no file ID) carrying the embedded study's accession as its study ID.
    Accessions that appear only in per-category ``*_files`` lists must not be tracked.
    """
    config = joint_fixture.config

    await joint_fixture.kafka.publish_event(
        payload=_embedded_dataset_payload(),
        type_=config.resource_upsertion_type,
        topic=config.resource_change_topic,
        key="dataset_embedded_GHGAD1",
    )
    await joint_fixture.event_subscriber.run(forever=False)

    collection = _file_accession_collection(joint_fixture)
    stored = {doc["_id"]: doc for doc in collection.find({})}
    assert set(stored) == _PAYLOAD_FILE_ACCESSIONS
    # An accession only present in a per-category file list must not have been tracked.
    assert "GHGAF_IGNORED" not in stored
    for doc in stored.values():
        assert doc["study_id"] == "GHGAS1"
        assert doc["file_id"] is None
        assert doc["mapped"] is None
        assert doc["created"] is not None


async def test_existing_file_accession_study_is_updated(joint_fixture: JointFixture):
    """Study IDs are set on unmapped file accessions whose study differs.

    An accession already mapped to a file ID (and study) must be left untouched, while
    an unmapped accession gets its study ID set whether it had none yet or a different
    one. An unmapped accession that already carries the same study ID stays as is.
    """
    config = joint_fixture.config

    mapped_file_id = uuid4()
    async with MongoKafkaDaoPublisherFactory.construct(
        config=config
    ) as dao_publisher_factory:
        dao = await get_file_accession_dao(
            config=config, dao_publisher_factory=dao_publisher_factory
        )
        # Already known and mapped to a different study - must not change.
        await dao.upsert(
            FileAccession(pid="GHGAF1", file_id=mapped_file_id, study_id="OTHER_STUDY")
        )
        # Already known but without a study ID yet - must get the study ID set.
        await dao.upsert(FileAccession(pid="GHGAF2"))
        # Unmapped but tracked under a different study - must be updated.
        await dao.upsert(FileAccession(pid="GHGAF4", study_id="OTHER_STUDY"))

    await joint_fixture.kafka.publish_event(
        payload=_embedded_dataset_payload(),
        type_=config.resource_upsertion_type,
        topic=config.resource_change_topic,
        key="dataset_embedded_GHGAD1",
    )
    await joint_fixture.event_subscriber.run(forever=False)

    collection = _file_accession_collection(joint_fixture)
    stored = {doc["_id"]: doc for doc in collection.find({})}
    assert set(stored) == _PAYLOAD_FILE_ACCESSIONS

    # The pre-existing mapped accession keeps its original study and file ID.
    assert stored["GHGAF1"]["study_id"] == "OTHER_STUDY"
    assert UUID(str(stored["GHGAF1"]["file_id"])) == mapped_file_id

    # The previously unmapped accession without a study got it set, still no file ID.
    assert stored["GHGAF2"]["study_id"] == "GHGAS1"
    assert stored["GHGAF2"]["file_id"] is None

    # The unmapped accession tracked under a different study was updated, still no
    # file ID.
    assert stored["GHGAF4"]["study_id"] == "GHGAS1"
    assert stored["GHGAF4"]["file_id"] is None

    # Newly seen accessions were created with the study ID.
    assert stored["GHGAF3"]["study_id"] == "GHGAS1"
    assert stored["GHGAF3"]["file_id"] is None


async def test_registry_study_queries(joint_fixture: JointFixture):
    """The registry can look up a single study and list studies with an unmapped filter.

    After consuming a resource that stores a study and tracks its (unmapped) file
    accessions, the study is retrievable by ID and appears in the listing. It is
    included by the ``with_unmapped_files`` filter while any of its accessions lack a
    file ID, and drops out of that filtered listing once all of them have been mapped.
    """
    config = joint_fixture.config
    registry = joint_fixture.registry

    await joint_fixture.kafka.publish_event(
        payload=_embedded_dataset_payload(),
        type_=config.resource_upsertion_type,
        topic=config.resource_change_topic,
        key="dataset_embedded_GHGAD1",
    )
    await joint_fixture.event_subscriber.run(forever=False)

    # A single study can be looked up by its ID.
    study = await registry.get_study("GHGAS1")
    assert study.id == "GHGAS1"
    assert study.title == "A test study"

    # An unknown study ID raises a StudyNotFoundError.
    with pytest.raises(RegistryPort.StudyNotFoundError):
        await registry.get_study("DOES_NOT_EXIST")

    # The unfiltered listing returns the study.
    assert [study.id for study in await registry.get_studies()] == ["GHGAS1"]

    # The study has unmapped file accessions, so it matches the filter.
    filtered = await registry.get_studies(with_unmapped_files=True)
    assert [study.id for study in filtered] == ["GHGAS1"]

    # Map all of the study's file accessions to internal file IDs.
    async with MongoKafkaDaoPublisherFactory.construct(
        config=config
    ) as dao_publisher_factory:
        dao = await get_file_accession_dao(
            config=config, dao_publisher_factory=dao_publisher_factory
        )
        for accession in _PAYLOAD_FILE_ACCESSIONS:
            await dao.upsert(
                FileAccession(pid=accession, file_id=uuid4(), study_id="GHGAS1")
            )

    # With no unmapped accessions left, the study drops out of the filtered listing,
    # but is still returned by the unfiltered one.
    assert await registry.get_studies(with_unmapped_files=True) == []
    assert [study.id for study in await registry.get_studies()] == ["GHGAS1"]


async def test_searchable_resource_deletion_is_consumed(joint_fixture: JointFixture):
    """A deletion event (carrying only SearchableResourceInfo) is consumed without
    error.
    """
    config = joint_fixture.config

    await joint_fixture.kafka.publish_event(
        payload={"accession": "GHGA:STUDY1", "class_name": "Study"},
        type_=config.resource_deletion_type,
        topic=config.resource_change_topic,
        key="dataset_embedded_GHGA:STUDY1",
    )
    await joint_fixture.event_subscriber.run(forever=False)

    assert _study_count(joint_fixture) == 0
