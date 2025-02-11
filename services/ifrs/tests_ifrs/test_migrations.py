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
"""Tests for database migrations"""

from random import randint

import pytest
from ghga_service_commons.utils.multinode_storage import (
    S3ObjectStorageNodeConfig,
    S3ObjectStoragesConfig,
)
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.providers.s3.testutils import S3Fixture, temp_file_object
from motor.motor_asyncio import AsyncIOMotorClient

from ifrs.core.models import FileMetadataBase
from ifrs.migration_logic._manager import MigrationStepError
from ifrs.migration_logic._utils import MigrationDefinition
from ifrs.migrations import run_db_migrations
from tests_ifrs.fixtures.config import get_config
from tests_ifrs.fixtures.example_data import EXAMPLE_METADATA_BASE


@pytest.mark.asyncio
async def test_v2_migration(
    mongodb: MongoDbFixture,
    s3: S3Fixture,
    populate_s3_buckets,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test the migration script for v2 where we add the size of the encrypted object
    to the docs in the file_metadata collection.
    """
    # Create the test config for the object storage
    node_config = S3ObjectStorageNodeConfig(bucket="permanent", credentials=s3.config)
    object_storage_config = S3ObjectStoragesConfig(
        object_storages={
            "test": node_config,
        }
    )

    # Patch the config
    config = get_config(sources=[mongodb.config, object_storage_config])
    monkeypatch.setattr("ifrs.migration_logic.ifrs_migrations.Config", lambda: config)
    client = mongodb.client
    coll = client[config.db_name]["file_metadata"]

    # Set up test data - we want some random object sizes to verify we're not accidentally
    #  reading some dummy value somewhere. Record the sizes so we can check later that
    #  what we retrieve is correct.
    test_data_sizes = {}
    base = EXAMPLE_METADATA_BASE.model_dump()
    base.pop("file_id")
    for n in range(1, 10):
        metadata_base = base.copy()
        metadata_base["_id"] = f"examplefile00{n}"
        metadata_base["object_id"] = f"objectid00{n}"
        size = randint(1000, 4000)
        test_data_sizes[metadata_base["_id"]] = size
        coll.insert_one(metadata_base)

        # Upload a temp file object with the given size to our S3 fixture
        with temp_file_object(
            bucket_id="permanent", object_id=f"objectid00{n}", size=size
        ) as f:
            await s3.populate_file_objects([f])

    post_insert = coll.find().to_list()
    assert len(post_insert) == 9
    for doc in post_insert:
        assert "object_size" not in doc

    # Run the database migrations, which should create the lock/versioning collection
    #  and then update the 'file_metadata' collection.
    await run_db_migrations(config=config)

    # Make sure the docs from file_metadata were updated with the right size values
    post_apply = coll.find().to_list()
    assert len(post_apply) == 9
    for doc in post_apply:
        assert "object_size" in doc
        assert doc["object_size"] == test_data_sizes[doc["_id"]]

    # Unapply the v2 migration, which will fail because the current model requires
    #  the `object_size` field.
    with pytest.raises(MigrationStepError):
        await run_db_migrations(config=config, target_version=1)

    # Make sure the docs from file_metadata were updated with the right size values
    post_failed_unapply = coll.find().to_list()
    assert len(post_failed_unapply) == 9
    for doc in post_failed_unapply:
        assert "object_size" in doc
        assert doc["object_size"] == test_data_sizes[doc["_id"]]

    # Monkeypatch the pydantic model to resemble the old version so we can test reversal
    class PatchedFileMetadata(FileMetadataBase):
        object_id: str

    monkeypatch.setattr(
        "ifrs.migration_logic.ifrs_migrations.FileMetadata", PatchedFileMetadata
    )
    await run_db_migrations(config=config, target_version=1)

    post_unapply = coll.find().to_list()
    assert len(post_unapply) == 9
    for doc in post_unapply:
        assert "object_size" not in doc


@pytest.mark.asyncio
async def test_drop_or_rename_nonexistent_collection(mongodb: MongoDbFixture):
    """Run migrations on a DB with no data in it.

    The migrations should still complete and log the new DB version.
    """
    config = get_config(sources=[mongodb.config])
    client = mongodb.client
    version_coll = client[config.db_name][config.db_version_collection]
    versions = version_coll.find().to_list()
    assert not versions

    await run_db_migrations(config=config)

    versions = version_coll.find().to_list()
    assert len(versions) == 2


@pytest.mark.asyncio
async def test_stage_unstage(mongodb: MongoDbFixture):
    """Stage and immediately unstage a collection with collection name collisions."""
    config = get_config(sources=[mongodb.config])
    client: AsyncIOMotorClient = AsyncIOMotorClient(
        str(config.mongo_dsn.get_secret_value())
    )
    db = client.get_database(config.db_name)
    coll_name = "coll1"
    collection = client[config.db_name][coll_name]

    # Insert a dummy doc so our migration has something to do
    await collection.insert_one({"field": "test"})

    async def change_function(doc):
        """Dummy change function for running `migration_docs_in_collection`"""
        return doc

    class TestMig(MigrationDefinition):
        version = 2

        async def apply(self):
            await self.migrate_docs_in_collection(
                coll_name=coll_name,
                change_function=change_function,
            )
            # Create tmp_v2_old_coll1 for name collision upon staging 'coll1'
            # The correct behavior is to drop the collection upon rename if it exists
            temp_coll = client[config.db_name][f"tmp_v2_old_{coll_name}"]
            await temp_coll.insert_one({"some": "document"})
            await self.stage_collection(coll_name)

            # Create tmp_v2_new_coll1 for name collision upon unstaging 'coll1'
            temp_coll = client[config.db_name][f"tmp_v2_new_{coll_name}"]
            await temp_coll.insert_one({"some": "document"})
            await self.unstage_collection(coll_name)

    migdef = TestMig(db=db, is_final_migration=False, unapplying=False)
    await migdef.apply()
