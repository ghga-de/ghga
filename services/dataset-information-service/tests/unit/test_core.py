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

"""Unit tests for the core class"""

from unittest.mock import AsyncMock
from uuid import uuid4

import ghga_event_schemas.pydantic_ as event_schemas
import pytest

from dins.core.models import DatasetFileAccessions, PendingFileInfo
from tests.fixtures.joint import JointRig
from tests.fixtures.utils import (
    make_accession_map,
    make_file_information,
    make_file_internally_registered,
    make_metadata_dataset_overview,
)

pytestmark = pytest.mark.asyncio


async def test_register_dataset_information_happy(rig: JointRig):
    """Test that we can register new dataset_information"""
    dataset = make_metadata_dataset_overview()
    await rig.information_service.register_dataset_information(dataset=dataset)

    stored = await rig.dataset_dao.get_by_id("DS001")
    expected = DatasetFileAccessions(
        accession="DS001", file_accessions=["GHGA001", "GHGA002"]
    )
    assert stored == expected


async def test_register_dataset_information_update(rig: JointRig):
    """Test that datasets are updated"""
    dataset = make_metadata_dataset_overview(
        files=[
            event_schemas.MetadataDatasetFile(
                accession="GHGA001", description=None, file_extension=".bam"
            ),
        ],
    )
    await rig.information_service.register_dataset_information(dataset=dataset)

    # Update and run again
    dataset.files.append(
        event_schemas.MetadataDatasetFile(
            accession="GHGA002", description=None, file_extension=".bam"
        )
    )
    await rig.information_service.register_dataset_information(dataset=dataset)

    stored = [x async for x in rig.dataset_dao.find_all(mapping={"accession": "DS001"})]
    assert len(stored) == 1

    # DINS doesn't store MetadataDatasetOverview directly. Like the F.I.R. event, it
    #  stores a subset of the information. So build that expected model and compare.
    expected = DatasetFileAccessions(
        accession="DS001", file_accessions=["GHGA001", "GHGA002"]
    )
    assert stored[0] == expected


async def test_delete_dataset_information(rig: JointRig):
    """Test deleting dataset information in all cases:

    1. Dataset exists and gets deleted successfully
    2. Dataset does not exist and deletion method quietly exits.
    """
    dataset_file_accessions = DatasetFileAccessions(
        accession="DS001", file_accessions=["GHGA001", "GHGA002"]
    )
    await rig.dataset_dao.insert(dataset_file_accessions)

    await rig.information_service.delete_dataset_information(dataset_id="DS001")
    remaining = rig.dataset_dao.find_all(mapping={"accession": "DS001"})
    assert len([x async for x in remaining]) == 0

    # Deleting a non-existent dataset should not raise an error
    await rig.information_service.delete_dataset_information(dataset_id="DS001")


async def test_register_file_information_happy(rig: JointRig):
    """Test that we can register new file information when it doesn't already exist"""
    file_information = make_file_information()
    await rig.information_service.register_file_information(
        file_information=file_information
    )

    stored = await rig.file_information_dao.get_by_id(file_information.accession)
    assert stored == file_information


async def test_register_file_information_duplicate(rig: JointRig):
    """Test that duplicate FileInformation is ignored if received for registration"""
    file_information = make_file_information()
    await rig.information_service.register_file_information(
        file_information=file_information
    )
    await rig.information_service.register_file_information(
        file_information=file_information
    )

    stored = rig.file_information_dao.find_all(
        mapping={"accession": file_information.accession}
    )
    assert len([x async for x in stored]) == 1


async def test_register_file_information_conflict(rig: JointRig):
    """Test that registering conflicting FileInformation raises an error."""
    file_information = make_file_information()
    await rig.information_service.register_file_information(
        file_information=file_information
    )

    conflicting = make_file_information(accession=file_information.accession)
    conflicting.storage_alias = "different-node"
    with pytest.raises(
        rig.information_service.MismatchingFileInformationAlreadyRegistered
    ):
        await rig.information_service.register_file_information(
            file_information=conflicting
        )


async def test_delete_file_information(rig: JointRig):
    """Test that FileInformation deletion works both when the data exists
    as well as when it doesn't.
    """
    file_id = uuid4()
    accession_map = make_accession_map(accession="GHGA001", file_id=file_id)
    await rig.accession_map_dao.insert(accession_map)
    file_information = make_file_information(accession="GHGA001")
    await rig.file_information_dao.insert(file_information)

    await rig.information_service.delete_file_information(file_id=file_id)
    remaining = rig.file_information_dao.find_all(mapping={"accession": "GHGA001"})
    assert len([x async for x in remaining]) == 0

    # Deleting when no accession map exists should not raise an error
    await rig.information_service.delete_file_information(file_id=uuid4())


async def test_handle_file_internally_registered(rig: JointRig):
    """Test that FileInternallyRegistered events are handled correctly.

    This test just checks for method selection, nothing more.
    If the corresponding accession map already exists, then `register_file_information`
    should be called (further checks and guards are handled within that method).

    If no accession map yet exists, then call `store_pending_file_info()`.
    """
    fir_event_payload = make_file_internally_registered()
    store_mock = AsyncMock()
    rig.information_service.store_pending_file_info = store_mock  # type: ignore

    await rig.information_service.handle_file_internally_registered(
        file=fir_event_payload
    )
    store_mock.assert_awaited_once()
    store_mock.reset_mock()

    # Now insert an accession map
    accession_map = make_accession_map(
        accession="GHGA001", file_id=fir_event_payload.file_id
    )
    await rig.accession_map_dao.insert(accession_map)

    register_mock = AsyncMock()
    rig.information_service.register_file_information = register_mock  # type: ignore
    await rig.information_service.handle_file_internally_registered(
        file=fir_event_payload
    )
    store_mock.assert_not_awaited()
    register_mock.assert_awaited_once()


async def test_store_pending_file_info_happy(rig: JointRig):
    """Test that FileInternallyRegistered payloads are stored as PendingFileInfo."""
    fir_event_payload = make_file_internally_registered()
    await rig.information_service.handle_file_internally_registered(
        file=fir_event_payload
    )

    stored_data = await rig.pending_file_info_dao.get_by_id(fir_event_payload.file_id)
    expected_data = PendingFileInfo(
        file_id=fir_event_payload.file_id,
        decrypted_size=fir_event_payload.decrypted_size,
        decrypted_sha256=fir_event_payload.decrypted_sha256,
        storage_alias=fir_event_payload.storage_alias,
    )
    assert stored_data == expected_data


async def test_store_pending_file_info_duplicate(rig: JointRig):
    """Test that duplicate PendingFileInfo does not cause an error"""
    fir_event_payload = make_file_internally_registered()
    await rig.information_service.handle_file_internally_registered(
        file=fir_event_payload
    )
    await rig.information_service.handle_file_internally_registered(
        file=fir_event_payload
    )

    # Make sure only one record exists
    stored_data = rig.pending_file_info_dao.find_all(
        mapping={"file_id": fir_event_payload.file_id}
    )
    assert len([x async for x in stored_data]) == 1


async def test_store_pending_file_info_conflict(rig: JointRig):
    """Test that an error is raised if new PendingFileInfo conflicts with existing data"""
    fir_event_payload = make_file_internally_registered()
    pending = PendingFileInfo(
        file_id=fir_event_payload.file_id,
        decrypted_size=fir_event_payload.decrypted_size,
        decrypted_sha256=fir_event_payload.decrypted_sha256,
        storage_alias=fir_event_payload.storage_alias,
    )
    await rig.information_service.store_pending_file_info(pending=pending)

    conflicting = PendingFileInfo(
        file_id=fir_event_payload.file_id,
        decrypted_size=fir_event_payload.decrypted_size,
        decrypted_sha256=fir_event_payload.decrypted_sha256,
        storage_alias="different-data-hub",
    )
    with pytest.raises(rig.information_service.MismatchingPendingFileInfoExists):
        await rig.information_service.store_pending_file_info(pending=conflicting)


async def test_store_accession_map_happy(rig: JointRig):
    """Test that new accession map data is stored without problems"""
    accession_map = make_accession_map()
    await rig.information_service.store_accession_map(accession_map=accession_map)

    stored_map = await rig.accession_map_dao.get_by_id(accession_map.accession)
    assert stored_map == accession_map


async def test_store_accession_map_updates(rig: JointRig):
    """Test that accession maps can be updated as long as no file is yet registered.

    Also test that an error is raised when trying to update an accession map once
    a matching file is already registered.
    """
    accession = "GHGA001"
    accession_map1 = make_accession_map(accession=accession)
    await rig.information_service.store_accession_map(accession_map=accession_map1)

    # Update to a different file id - should succeed since no FileInformation exists yet
    file_id = uuid4()
    accession_map2 = make_accession_map(accession=accession, file_id=file_id)
    await rig.information_service.store_accession_map(accession_map=accession_map2)
    stored_map = await rig.accession_map_dao.get_by_id(accession)
    assert stored_map == accession_map2

    # Insert a FileInformation object for the file ID on the accession map
    file_information = make_file_information(accession)
    await rig.file_information_dao.insert(file_information)

    # Switching the file ID for an accession that already has FileInformation
    #  should raise an error
    accession_map3 = make_accession_map(accession=accession)
    with pytest.raises(
        rig.information_service.MismatchingFileInformationAlreadyRegistered
    ):
        await rig.information_service.store_accession_map(accession_map=accession_map3)


async def test_delete_accession_map(rig: JointRig):
    """Test that the accession map deletion method works when the map
    exists as well as when it doesn't exist.
    """
    accession_map = make_accession_map()
    accession = accession_map.accession
    await rig.accession_map_dao.insert(accession_map)

    await rig.information_service.delete_accession_map(accession=accession)
    remaining = rig.accession_map_dao.find_all(mapping={"accession": accession})
    assert len([x async for x in remaining]) == 0

    # Deleting a non-existent accession map should not raise an error
    await rig.information_service.delete_accession_map(accession=accession)
