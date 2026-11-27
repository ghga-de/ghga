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

"""Test the order in which the waiting files are served, against MongoDB"""

from collections.abc import Sequence
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from pydantic import UUID4

from fis.constants import (
    BOX_PRIORITY_EVENT_KEY,
    FILES_COLLECTION,
    MAX_FILES_PER_REQUEST,
)
from fis.core.models import (
    BaseFileInformation,
    FileUnderInterrogation,
    UploadBoxPriority,
    UploadBoxPriorityEntry,
)
from hexkit.providers.mongodb import ConfiguredMongoClient
from hexkit.utils import now_utc_ms_prec
from tests_fis.fixtures.joint import JointFixture
from tests_fis.fixtures.utils import create_file_under_interrogation

pytestmark = pytest.mark.asyncio

HUB1 = "HUB1"
HUB2 = "HUB2"
LEASE_FIELDS = ["leased_until", "leased_by", "claimed_at", "times_claimed"]


async def _insert_files(
    joint_fixture: JointFixture, *, box_id: UUID4 | None, count: int = 1
) -> list[FileUnderInterrogation]:
    """Insert `count` waiting files of HUB1 in the given box"""
    files: list[FileUnderInterrogation] = []
    for _ in range(count):
        file = create_file_under_interrogation(HUB1).model_copy(
            update={"box_id": box_id}
        )
        await joint_fixture.file_dao.insert(file)
        files.append(file)
    return files


async def _store_priority(joint_fixture: JointFixture, *, box_ids: list[UUID4]):
    """Store an upload box priority list with the given boxes"""
    await joint_fixture.interrogation_handler.store_upload_box_priority(
        priority=UploadBoxPriority(
            id=BOX_PRIORITY_EVENT_KEY,
            version=1,
            entries=[UploadBoxPriorityEntry(box_id=box_id) for box_id in box_ids],
        )
    )


def _ids(files: Sequence[BaseFileInformation]) -> list[UUID4]:
    """Return the IDs of the files, in order"""
    return [file.id for file in files]


async def test_files_of_listed_boxes_come_first(joint_fixture: JointFixture):
    """Files of listed boxes come first, in list order. Files of the same box, and
    files without a listed box, come in `id` order.
    """
    first_box, second_box = uuid4(), uuid4()
    first_box_files = await _insert_files(joint_fixture, box_id=first_box, count=2)
    second_box_files = await _insert_files(joint_fixture, box_id=second_box, count=2)
    unlisted_box_files = await _insert_files(joint_fixture, box_id=uuid4())
    files_without_box = await _insert_files(joint_fixture, box_id=None, count=2)

    # Files stored before FIS kept the box ID have no box_id field at all
    with ConfiguredMongoClient(config=joint_fixture.config) as client:
        client[joint_fixture.config.db_name][FILES_COLLECTION].update_one(
            {"_id": files_without_box[0].id}, {"$unset": {"box_id": ""}}
        )

    # Files that don't wait for interrogation, or wait in another storage
    other_hub_file = create_file_under_interrogation(HUB2)
    other_hub_file.box_id = first_box
    interrogated_file = create_file_under_interrogation(HUB1)
    interrogated_file.box_id = first_box
    interrogated_file.state = "interrogated"
    interrogated_file.interrogated = True
    cancelled_file = create_file_under_interrogation(HUB1)
    cancelled_file.box_id = first_box
    cancelled_file.state = "cancelled"
    for file in [other_hub_file, interrogated_file, cancelled_file]:
        await joint_fixture.file_dao.insert(file)

    await _store_priority(joint_fixture, box_ids=[first_box, second_box])

    waiting_files = await joint_fixture.interrogation_queue.get_waiting_files(
        storage_alias=HUB1, limit=10
    )

    assert _ids(waiting_files) == [
        *sorted(_ids(first_box_files)),
        *sorted(_ids(second_box_files)),
        *sorted(_ids(unlisted_box_files + files_without_box)),
    ]
    # The adapter maps `_id` back to `id` and keeps the other fields
    first_file = min(first_box_files, key=lambda file: file.id)
    assert waiting_files[0] == BaseFileInformation(**first_file.model_dump())


@pytest.mark.parametrize("stored_list", ["missing", "empty"])
async def test_files_without_a_priority_list(
    joint_fixture: JointFixture, stored_list: str
):
    """Without a list, or with an empty one, files come in `id` order"""
    files: list[FileUnderInterrogation] = []
    for _ in range(3):
        files.extend(await _insert_files(joint_fixture, box_id=uuid4(), count=2))
    if stored_list == "empty":
        await _store_priority(joint_fixture, box_ids=[])

    waiting_files = await joint_fixture.interrogation_queue.get_waiting_files(
        storage_alias=HUB1, limit=10
    )

    assert _ids(waiting_files) == sorted(_ids(files))


async def test_only_the_highest_ranked_files_are_served(joint_fixture: JointFixture):
    """With more waiting files than `MAX_FILES_PER_REQUEST`, exactly the highest-ranked
    files are served.
    """
    first_box, second_box = uuid4(), uuid4()
    second_box_files = await _insert_files(joint_fixture, box_id=second_box, count=3)
    first_box_files = await _insert_files(joint_fixture, box_id=first_box, count=3)
    await _insert_files(joint_fixture, box_id=None)
    await _store_priority(joint_fixture, box_ids=[first_box, second_box])

    served_files = (
        await joint_fixture.interrogation_handler.get_files_not_yet_interrogated(
            storage_alias=HUB1
        )
    )

    expected_ids = [*sorted(_ids(first_box_files)), *sorted(_ids(second_box_files))]
    assert len(served_files) == MAX_FILES_PER_REQUEST == 5
    assert _ids(served_files) == expected_ids[:MAX_FILES_PER_REQUEST]


async def test_files_after_a_deleted_priority_event(joint_fixture: JointFixture):
    """After a `deleted` priority event, files come in `id` order only"""
    first_box, second_box = uuid4(), uuid4()
    files = [
        *await _insert_files(joint_fixture, box_id=second_box, count=2),
        *await _insert_files(joint_fixture, box_id=first_box, count=2),
    ]
    await _store_priority(joint_fixture, box_ids=[first_box, second_box])

    await joint_fixture.kafka.publish_event(
        payload={},
        type_="deleted",
        topic=joint_fixture.config.upload_box_priority_topic,
        key=BOX_PRIORITY_EVENT_KEY,
    )
    await joint_fixture.outbox_consumer.run(forever=False)

    waiting_files = await joint_fixture.interrogation_queue.get_waiting_files(
        storage_alias=HUB1, limit=10
    )

    assert _ids(waiting_files) == sorted(_ids(files))


async def test_claimable_files_order(joint_fixture: JointFixture):
    """Within a box, files never claimed come first, in `state_updated` order. Files
    whose lease ran out follow once those are leased, earliest first. Files still
    leased are left out.

    The expired files have the oldest `state_updated`, in reverse, so a sort by
    `state_updated` alone would fail.
    """
    box_id = uuid4()
    claim_time = now_utc_ms_prec()

    def make_file(**update: Any) -> FileUnderInterrogation:
        """Make a waiting file of HUB1 in the box, with the given fields"""
        return create_file_under_interrogation(HUB1).model_copy(
            update={"box_id": box_id, **update}
        )

    older_unclaimed = make_file(state_updated=claim_time - timedelta(minutes=5))
    newer_unclaimed = make_file(state_updated=claim_time - timedelta(minutes=1))
    long_expired = make_file(
        state_updated=claim_time - timedelta(minutes=30),
        leased_until=claim_time - timedelta(minutes=10),
        times_claimed=1,
    )
    recently_expired = make_file(
        state_updated=claim_time - timedelta(minutes=60),
        leased_until=claim_time - timedelta(minutes=1),
        times_claimed=1,
    )
    leased = make_file(leased_until=claim_time + timedelta(minutes=10), times_claimed=1)
    for file in [
        newer_unclaimed,
        recently_expired,
        leased,
        older_unclaimed,
        long_expired,
    ]:
        await joint_fixture.file_dao.insert(file)

    # Files stored before FIS kept leases have no lease fields at all
    with ConfiguredMongoClient(config=joint_fixture.config) as client:
        client[joint_fixture.config.db_name][FILES_COLLECTION].update_one(
            {"_id": older_unclaimed.id}, {"$unset": dict.fromkeys(LEASE_FIELDS, "")}
        )

    # While never-claimed files wait, the expired leases are held back
    claimable_files = await joint_fixture.interrogation_queue.get_claimable_files(
        storage_alias=HUB1, claim_time=claim_time, limit=10
    )
    assert _ids(claimable_files) == _ids([older_unclaimed, newer_unclaimed])

    # Lease the never-claimed files, and the expired leases come up
    with ConfiguredMongoClient(config=joint_fixture.config) as client:
        client[joint_fixture.config.db_name][FILES_COLLECTION].update_many(
            {"_id": {"$in": _ids(claimable_files)}},
            {"$set": {"leased_until": claim_time + timedelta(minutes=10)}},
        )
    claimable_files = await joint_fixture.interrogation_queue.get_claimable_files(
        storage_alias=HUB1, claim_time=claim_time, limit=10
    )
    assert _ids(claimable_files) == _ids([long_expired, recently_expired])


async def test_claimable_files_come_from_the_top_box(joint_fixture: JointFixture):
    """Claimable files come only from the highest-priority box that has any. Once all
    of its files are leased, the next box's files come up.
    """
    first_box, second_box = uuid4(), uuid4()
    first_box_files = await _insert_files(joint_fixture, box_id=first_box, count=2)
    second_box_files = await _insert_files(joint_fixture, box_id=second_box, count=2)
    unlisted_box_files = await _insert_files(joint_fixture, box_id=uuid4())
    await _store_priority(joint_fixture, box_ids=[first_box, second_box])

    claim_time = now_utc_ms_prec()
    for box_files in [first_box_files, second_box_files, unlisted_box_files]:
        claimable_files = await joint_fixture.interrogation_queue.get_claimable_files(
            storage_alias=HUB1, claim_time=claim_time, limit=10
        )
        assert sorted(_ids(claimable_files)) == sorted(_ids(box_files))
        for file in box_files:
            file.leased_until = claim_time + timedelta(minutes=10)
            await joint_fixture.file_dao.update(file)

    assert (
        await joint_fixture.interrogation_queue.get_claimable_files(
            storage_alias=HUB1, claim_time=claim_time, limit=10
        )
        == []
    )


async def test_claim_query_uses_an_index(
    joint_fixture: JointFixture, monkeypatch: pytest.MonkeyPatch
):
    """The claim query finds its files through an index, not a collection scan.

    `$or` plans as one index scan per branch, so the test checks for the absence of
    a COLLSCAN rather than for a single IXSCAN.
    """
    box_id = uuid4()
    await _insert_files(joint_fixture, box_id=box_id, count=3)
    await _store_priority(joint_fixture, box_ids=[box_id])
    queue = joint_fixture.interrogation_queue
    collection = queue._collection  # type: ignore[attr-defined]
    pipelines: list[list[dict]] = []

    class RecordingCollection:
        """Records the pipeline of each aggregation before running it"""

        async def aggregate(self, pipeline: list[dict]) -> Any:
            """Record the pipeline, then run it"""
            pipelines.append(pipeline)
            return await collection.aggregate(pipeline)

    monkeypatch.setattr(queue, "_collection", RecordingCollection())
    await queue.get_claimable_files(
        storage_alias=HUB1, claim_time=now_utc_ms_prec(), limit=5
    )

    with ConfiguredMongoClient(config=joint_fixture.config) as client:
        explanation = str(
            client[joint_fixture.config.db_name].command(
                "aggregate", FILES_COLLECTION, pipeline=pipelines[0], explain=True
            )
        )
    assert "IXSCAN" in explanation
    assert "COLLSCAN" not in explanation
