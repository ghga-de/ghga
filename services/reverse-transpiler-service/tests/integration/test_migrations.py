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

"""Tests for DB migrations"""

from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from gridfs import GridFS, GridFSBucket
from hexkit.providers.mongodb.testutils import MongoDbFixture
from openpyxl import Workbook

from rts.adapters.outbound.dao import GridFSDaoFactory
from rts.core.rev_tran import ReverseTranspiler
from rts.migrations.entry import run_db_migrations
from rts.models import StudyMetadata
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()

METADATA = "metadata"
WORKBOOKS = "workbooks"


async def store_workbook_old_code(grid_fs: GridFS, workbook: Workbook, accession: str):
    """Store a workbook in grid fs using the old code before the v2 changes"""
    # Convert the workbook to a bytestream
    workbook_bytestream = BytesIO()
    workbook.save(workbook_bytestream)
    workbook_bytestream.seek(0)

    # Insert new file
    grid_fs.put(data=workbook_bytestream, _id=accession, filename=f"{accession}.xlsx")


async def test_v2_migration(mongodb: MongoDbFixture):
    """Test the v2 migration.

    Insert some StudyMetadata documents into the metadata collection, run the migration.
    Expected results:
    - Workbook data has been moved to 'workbooks' GridFS bucket, deleted from default bucket
    - Metadata is stored in 'metadata' GridFS bucket
    - MongoDB collection 'metadata' has been dropped

    Then reverse the migration and verify changes have been reversed.
    """
    config = get_config(sources=[mongodb.config])
    db = mongodb.client.get_database(config.db_name)
    sync_grid_fs = GridFS(db)
    default_bucket = GridFSBucket(db)
    workbooks_bucket = GridFSBucket(db, WORKBOOKS)
    metadata_bucket = GridFSBucket(db, METADATA)
    collection = db[METADATA]

    reverse_transpiler = ReverseTranspiler(
        config=config, metadata_dao=AsyncMock(), workbook_dao=AsyncMock()
    )

    # Load workbook data
    with open("tests/fixtures/test_artifact.json") as file:
        study_metadata_json = file.read()

    study_metadata = StudyMetadata.model_validate_json(study_metadata_json)
    metadata_docs = []
    workbooks = []

    # Make multiple copies of that data just with a new accession each time
    for i in range(5):
        accession = f"test{i}"
        metadata = study_metadata.model_copy(update={"study_accession": accession})
        doc = metadata.model_dump()
        doc["_id"] = doc.pop("study_accession")
        metadata_docs.append(doc)
        workbook = reverse_transpiler._reverse_transpile(study_metadata)
        workbooks.append(workbook)
        await store_workbook_old_code(
            grid_fs=sync_grid_fs, workbook=workbook, accession=accession
        )

    # Verify that the workbook data is now in the default bucket:
    populated_workbooks = default_bucket.find().to_list()
    assert len(populated_workbooks) == 5
    assert all(file.filename.endswith(".xlsx") for file in populated_workbooks)

    # Insert the documents for the study metadata accompanying the workbook files
    collection.insert_many(metadata_docs)

    # Run the migration
    await run_db_migrations(config=config, target_version=2)

    # Check that the metadata collection got dropped:
    assert METADATA not in db.list_collection_names()

    # Verify that the workbooks were moved from the default bucket to 'workbooks' bucket
    assert not default_bucket.find().to_list()
    assert len(workbooks_bucket.find().to_list()) == 5

    # Check that the 'metadata' bucket now has items:
    metadata_grid_files = metadata_bucket.find().to_list()
    assert len(metadata_grid_files) == 5
    assert all(not file.filename.endswith(".xlsx") for file in metadata_grid_files)

    # Now check that the new code retrieves results properly (DAOs get correct data)
    async with GridFSDaoFactory.construct(config=config) as grid_fs_factory:
        metadata_dao = grid_fs_factory.get_metadata_dao()
        metadata_files = [x async for x in metadata_dao.find_all()]
        assert len(metadata_files) == len(metadata_docs)

        workbook_dao = grid_fs_factory.get_workbook_dao()
        workbook_files = [x async for x in workbook_dao.find_all()]
        assert len(workbook_files) == len(workbooks)

    # Reverse the migration
    await run_db_migrations(config=config, target_version=1)

    # Check that the workbooks data is gone from 'workbooks' bucket and back in default
    assert not workbooks_bucket.find().to_list()
    assert len(default_bucket.find().to_list()) == 5

    # Check that the metadata files are removed from the 'metadata' bucket:
    assert not metadata_bucket.find().to_list()

    async with GridFSDaoFactory.construct(config=config) as grid_fs_factory:
        metadata_dao = grid_fs_factory.get_metadata_dao()
        metadata_files = [x async for x in metadata_dao.find_all()]
        assert len(metadata_files) == 0

        # Verify that there are still workbooks, but the prefix is removed
        workbook_dao = grid_fs_factory.get_workbook_dao()
        workbook_files = [x async for x in workbook_dao.find_all()]
        assert len(workbook_files) == 0  # DAO sees nothing with the expected prefix

    # Refresh the metadata collection and verify the docs exist there again
    collection = db[METADATA]
    metadata_retrieved = collection.find().sort("_id").to_list()
    assert metadata_retrieved == metadata_docs
