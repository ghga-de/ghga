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

"""Test for the V3 DB migration"""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from hexkit.providers.mongodb.migrations import MigrationConfig
from hexkit.providers.mongodb.testutils import MongoDbFixture

from ars.migrations.entry import run_db_migrations

pytestmark = pytest.mark.asyncio()


async def test_v3_migration(mongodb: MongoDbFixture):
    """Test the apply/unapply functions of the V3Migration"""
    migration_config = MigrationConfig(
        mongo_dsn=mongodb.config.mongo_dsn,
        db_name=mongodb.config.db_name,
        db_version_collection="arsDbVersions",
        migration_max_wait_sec=15,
        migration_wait_sec=1,
    )
    db = mongodb.client[mongodb.config.db_name]
    collection = db["accessRequests"]
    collection.delete_many({})

    # Run the v2 migration first so it doesn't alter our test data
    await run_db_migrations(config=migration_config, target_version=2)

    raw_date = datetime(2025, 10, 10, 10, 10, 10, 123789, UTC)
    old_date = raw_date.isoformat()
    date_migrated = raw_date.replace(microsecond=124000)
    date_reverted = date_migrated.isoformat()
    optional_uuids = [str(uuid4()), None, str(uuid4())]
    optional_dates = [old_date, None, None]

    expected_migrated_requests: list[dict[str, Any]] = []
    expected_reverted_requests: list[dict[str, Any]] = []

    for i in range(3):
        request: dict[str, Any] = {
            "_id": str(uuid4()),
            "user_id": str(uuid4()),
            "iva_id": optional_uuids[i],
            "dataset_id": "GHGAD12345678901234",
            "email": "test@test.com",
            "request_text": "Access pls",
            "access_starts": old_date,
            "access_ends": old_date,
            "full_user_name": "George McGeorge",
            "request_created": old_date,
            "status": "allowed",
            "status_changed": optional_dates[i],
            "changed_by": optional_uuids[i],
            "__metadata__": {
                "correlation_id": str(uuid4()),
                "published": True,
                "deleted": False,
            },
            "dataset_title": "",
            "dac_alias": "",
            "dac_email": "test@test.com",
            "dataset_description": None,
            "ticket_id": None,
            "internal_note": None,
            "note_to_requester": None,
        }
        collection.insert_one(request)

        migrated_request = deepcopy(request)
        migrated_optional_uuid = UUID(optional_uuids[i]) if optional_uuids[i] else None
        migrated_request.update(
            {
                "_id": UUID(request["_id"]),
                "user_id": UUID(request["user_id"]),
                "iva_id": migrated_optional_uuid,
                "access_starts": date_migrated,
                "access_ends": date_migrated,
                "request_created": date_migrated,
                "status_changed": date_migrated if optional_dates[i] else None,
                "changed_by": migrated_optional_uuid,
            }
        )
        cid = request["__metadata__"]["correlation_id"]
        migrated_request["__metadata__"]["correlation_id"] = UUID(cid)
        expected_migrated_requests.append(migrated_request)

        # reuse request for reverted_request
        request["access_starts"] = date_reverted
        request["access_ends"] = date_reverted
        request["request_created"] = date_reverted
        if optional_dates[i]:
            request["status_changed"] = date_reverted
        expected_reverted_requests.append(request)

    # Include a deleted outbox event for testing:
    deleted_request: dict[str, Any] = {
        "_id": "c2b02269-4e93-4fb0-ae94-24231198228a",
        "__metadata__": {
            "correlation_id": "afa2451d-2a58-4c37-af11-9ab9012ba344",
            "published": True,
            "deleted": True,
        },
    }
    collection.insert_one(deleted_request)
    expected_reverted_requests.append(deleted_request)
    migrated_deleted_doc = deepcopy(deleted_request)
    migrated_deleted_doc["_id"] = UUID("c2b02269-4e93-4fb0-ae94-24231198228a")
    migrated_deleted_doc["__metadata__"]["correlation_id"] = UUID(
        "afa2451d-2a58-4c37-af11-9ab9012ba344"
    )
    expected_migrated_requests.append(migrated_deleted_doc)

    # Now run the migration
    await run_db_migrations(config=migration_config, target_version=3)

    # Get data, sort everything, and compare
    migrated_requests = collection.find({}).to_list()
    sort_func = lambda x: str(x["_id"])
    migrated_requests.sort(key=sort_func)
    expected_migrated_requests.sort(key=sort_func)
    expected_reverted_requests.sort(key=lambda x: x["_id"])

    assert migrated_requests == expected_migrated_requests

    # Revert the migration
    await run_db_migrations(config=migration_config, target_version=2)

    # Get data and compare
    reverted_requests = collection.find({}).to_list()
    reverted_requests.sort(key=sort_func)
    assert reverted_requests == expected_reverted_requests
