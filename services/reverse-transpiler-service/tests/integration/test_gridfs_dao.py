# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Tests for the GridFSDao class"""

from io import BytesIO
from unittest.mock import Mock

import pytest
from hexkit.providers.mongodb.testutils import MongoDbFixture

from rts.adapters.outbound.dao import GridFSDaoFactory
from rts.models import StudyMetadata
from rts.ports.outbound.dao import GridFSDao, ResourceNotFoundError
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()


def fake_save_factory(return_value: str):
    """Return a function that writes the value to a provided bytestream"""

    def fake_save(bytestream: BytesIO):
        """Used for mocking the `Workbook.save()` method"""
        bytestream.write(return_value.encode("utf-8"))

    return fake_save


async def test_absent_file(mongodb: MongoDbFixture):
    """Test deleting and finding files that don't exist."""
    config = get_config(sources=[mongodb.config])
    async with GridFSDaoFactory.construct(config=config) as gridfs_dao_factory:
        metadata_dao = gridfs_dao_factory.get_metadata_dao()

        with pytest.raises(ResourceNotFoundError):
            await metadata_dao.delete(filename="myfile")
        with pytest.raises(ResourceNotFoundError):
            await metadata_dao.find(filename="myfile")

        workbook_dao = gridfs_dao_factory.get_workbook_dao()
        with pytest.raises(ResourceNotFoundError):
            await workbook_dao.delete(filename="myfile")
        with pytest.raises(ResourceNotFoundError):
            await workbook_dao.find(filename="myfile")


async def test_proper_delete(mongodb: MongoDbFixture):
    """Test deleting files that do exist."""
    config = get_config(sources=[mongodb.config])
    async with GridFSDaoFactory.construct(config=config) as gridfs_dao_factory:
        metadata_dao = gridfs_dao_factory.get_metadata_dao()

        study_metadata = StudyMetadata(
            study_accession="test1", content={"some": "data"}
        )
        await metadata_dao.upsert(data=study_metadata, filename="myfile")

        check_metadata = await metadata_dao.find(filename="myfile")
        assert check_metadata.model_dump() == study_metadata.model_dump()

        await metadata_dao.delete(filename="myfile")
        with pytest.raises(ResourceNotFoundError):
            await metadata_dao.find(filename="myfile")

        # Test the workbook dao:
        workbook_dao = gridfs_dao_factory.get_workbook_dao()
        mock_workbook = Mock()
        mock_workbook.save = fake_save_factory("some data!")

        await workbook_dao.upsert(data=mock_workbook, filename="myfile")
        check_workbook = await workbook_dao.find(filename="myfile")
        assert check_workbook == b"some data!"

        await workbook_dao.delete(filename="myfile")
        with pytest.raises(ResourceNotFoundError):
            await workbook_dao.find(filename="myfile")


async def test_upsert(mongodb: MongoDbFixture):
    """Test upsertion with and without existing files"""
    config = get_config(sources=[mongodb.config])
    async with GridFSDaoFactory.construct(config=config) as gridfs_dao_factory:
        metadata_dao = gridfs_dao_factory.get_metadata_dao()
        study_metadata = StudyMetadata(
            study_accession="test1", content={"some": "data"}
        )
        await metadata_dao.upsert(data=study_metadata, filename="myfile")

        study_metadata2 = study_metadata.model_copy(update={"study_accession": "test2"})
        await metadata_dao.upsert(data=study_metadata2, filename="myfile")
        check_metadata = await metadata_dao.find(filename="myfile")
        assert check_metadata.study_accession == "test2"

        # Test the workbook dao:
        workbook_dao = gridfs_dao_factory.get_workbook_dao()
        mock_workbook = Mock()
        mock_workbook.save = fake_save_factory("some data!")

        await workbook_dao.upsert(data=mock_workbook, filename="myfile")

        mock_workbook.save = fake_save_factory("some other data!")
        await workbook_dao.upsert(data=mock_workbook, filename="myfile")
        check_workbook = await workbook_dao.find(filename="myfile")
        assert check_workbook == b"some other data!"


async def test_serializer_error(mongodb: MongoDbFixture):
    """Test errors that occur during serialization"""
    config = get_config(sources=[mongodb.config])
    async with GridFSDaoFactory.construct(config=config) as gridfs_dao_factory:
        metadata_dao = gridfs_dao_factory.get_metadata_dao()
        metadata = Mock()
        metadata.model_dump_json.side_effect = RuntimeError()
        with pytest.raises(GridFSDao.SerializationError):
            await metadata_dao.upsert(data=metadata, filename="myfile")

        # Test the workbook dao:
        workbook_dao = gridfs_dao_factory.get_workbook_dao()
        mock_workbook = Mock()
        mock_workbook.save.side_effect = RuntimeError()
        with pytest.raises(GridFSDao.SerializationError):
            await workbook_dao.upsert(data=mock_workbook, filename="myfile")


async def test_deserializer_error(mongodb: MongoDbFixture):
    """Test errors that occur during deserialization.

    We only test the metadata DAO here because the workbook DAO is stored in bytes,
    returned in bytes, and thus should always work.
    """
    config = get_config(sources=[mongodb.config])
    async with GridFSDaoFactory.construct(config=config) as gridfs_dao_factory:
        metadata_dao = gridfs_dao_factory.get_metadata_dao()
        metadata = Mock()
        metadata.model_dump_json.return_value = "Gibberish you can save but not get"
        await metadata_dao.upsert(data=metadata, filename="myfile")

        with pytest.raises(GridFSDao.DeserializationError):
            _ = await metadata_dao.find(filename="myfile")
