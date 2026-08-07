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

"""Tests for the V3 Migration"""

from copy import deepcopy

import pytest

from hexkit.providers.mongodb.testutils import MongoDbFixture
from tests.fixtures import fixture_config  # noqa: F401
from wps.migrations import run_db_migrations

pytestmark = pytest.mark.asyncio()

TEST_DATASET = {
    "_id": "GHGAD74914788657848",
    "stage": "download",
    "title": "The complete-K dataset",
    "description": "An interesting dataset K of complete example set",
    "files": [
        {"id": "GHGAF94650597594139", "extension": ".txt"},
        {"id": "GHGAF12465589121827", "extension": ".json"},
        {"id": "GHGAF87505694906232", "extension": ".vcf.gz"},
        {"id": "GHGAF96143900109767", "extension": ".vcf.gz"},
        {"id": "GHGAF17902430582098", "extension": ".fastq.gz"},
        {"id": "GHGAF43993828152551", "extension": ".fastq.gz"},
        {"id": "GHGAF78316435628398", "extension": ".fastq.gz"},
    ],
}

CORRECT_FILES = [
    {"accession": file["id"], "extension": file["extension"]}  # type: ignore
    for file in TEST_DATASET["files"]
]

CORRECT_DATASET = deepcopy(TEST_DATASET)
CORRECT_DATASET["files"] = CORRECT_FILES

# A dataset already in the new format (as if it was migrated in a prior partial run)
ALREADY_MIGRATED_DATASET = deepcopy(CORRECT_DATASET)
ALREADY_MIGRATED_DATASET["_id"] = "GHGAD87516091803761"


async def test_migration_v3(config, mongodb: MongoDbFixture):
    """Test the migration to DB version 3 and reversion to DB version 2."""
    db = mongodb.client[config.db_name]
    collection = db[config.datasets_collection]
    collection.delete_many({})

    # Insert old-format data (files with 'id' field)
    collection.insert_one(deepcopy(TEST_DATASET))

    # Advance to v2 first (v2 migration only touches workPackages, not datasets)
    await run_db_migrations(config=config, target_version=2)

    # Apply v3 migration
    await run_db_migrations(config=config, target_version=3)

    # Verify files were migrated from 'id' to 'accession'
    migrated = collection.find_one({"_id": TEST_DATASET["_id"]})
    assert migrated is not None
    assert migrated == CORRECT_DATASET

    # Revert to v2 and verify files went back to 'id'
    await run_db_migrations(config=config, target_version=2)
    reverted = collection.find_one({"_id": TEST_DATASET["_id"]})
    assert reverted is not None
    assert reverted == TEST_DATASET


async def test_migration_v3_partial(config, mongodb: MongoDbFixture):
    """Test that the v3 migration handles partially migrated data idempotently.

    If one dataset is already in the new format (accession) and another is still in the
    old format (id), the migration should transform the old one and leave the new one
    unchanged.
    """
    db = mongodb.client[config.db_name]
    collection = db[config.datasets_collection]
    collection.delete_many({})

    # One dataset in old format, one already in new format
    collection.insert_many([deepcopy(TEST_DATASET), deepcopy(ALREADY_MIGRATED_DATASET)])

    await run_db_migrations(config=config, target_version=2)
    await run_db_migrations(config=config, target_version=3)

    old_migrated = collection.find_one({"_id": TEST_DATASET["_id"]})
    assert old_migrated is not None
    assert old_migrated == CORRECT_DATASET

    already_migrated = collection.find_one({"_id": ALREADY_MIGRATED_DATASET["_id"]})
    assert already_migrated is not None
    assert already_migrated == ALREADY_MIGRATED_DATASET
