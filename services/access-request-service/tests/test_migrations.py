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

"""Tests for migrations to ensure the output is what we expect."""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from hexkit.providers.mongodb.migrations import MigrationConfig
from hexkit.providers.mongodb.testutils import MongoDbFixture

from ars.core.models import AccessRequestStatus
from ars.migrations import V2Migration, run_db_migrations

pytestmark = pytest.mark.asyncio()


ACCESS_REQUESTS_V1 = [
    {
        "id": "request-id-1",
        "user_id": "id-of-john-doe@ghga.de",
        "dataset_id": "DS003",
        "email": "me@john-doe.name",
        "request_text": "Can I access yet another dataset using this IVA?",
        "access_starts": "2025-03-28T14:43:13.375748Z",
        "access_ends": "2026-03-28T22:59:59.999000Z",
        "full_user_name": "Dr. John Doe",
        "request_created": "2025-03-28T14:43:13.375748Z",
        "status": AccessRequestStatus.PENDING,
    },
    {
        "id": "request-id-2",
        "user_id": "id-of-john-doe@ghga.de",
        "dataset_id": "DS003",
        "email": "me@john-doe.name",
        "request_text": "Can I access yet another dataset using this IVA?",
        "access_starts": "2025-03-28T14:43:13.375748Z",
        "access_ends": "2026-03-28T22:59:59.999000Z",
        "full_user_name": "Dr. John Doe",
        "request_created": "2025-03-28T14:43:13.375748Z",
        "status": AccessRequestStatus.PENDING,
    },
    {
        "id": "request-id-3",
        "user_id": "id-of-john-doe@ghga.de",
        "dataset_id": "DS003",
        "email": "me@john-doe.name",
        "request_text": "Can I access yet another dataset using this IVA?",
        "access_starts": "2025-03-28T14:43:13.375748Z",
        "access_ends": "2026-03-28T22:59:59.999000Z",
        "full_user_name": "Dr. John Doe",
        "request_created": "2025-03-28T14:43:13.375748Z",
        "status": AccessRequestStatus.PENDING,
    },
    {
        "id": "request-id-4",
        "user_id": "id-of-john-doe@ghga.de",
        "dataset_id": "DS003",
        "email": "me@john-doe.name",
        "request_text": "Can I access yet another dataset using this IVA?",
        "access_starts": "2025-03-28T14:43:13.375748Z",
        "access_ends": "2026-03-28T22:59:59.999000Z",
        "full_user_name": "Dr. John Doe",
        "request_created": "2025-03-28T14:43:13.375748Z",
        "status": AccessRequestStatus.PENDING,
    },
]


async def test_v2_migration(mongodb: MongoDbFixture):
    """Ensure the v2 migration populates the correct fields"""
    migration_config = MigrationConfig(
        mongo_dsn=mongodb.config.mongo_dsn,
        db_name=mongodb.config.db_name,
        db_version_collection="arsDbVersions",
        migration_max_wait_sec=15,
        migration_wait_sec=1,
    )
    db = mongodb.client[mongodb.config.db_name]

    access_request_collection = db["accessRequests"]

    # Insert some access requests and datasets
    for access_request in ACCESS_REQUESTS_V1:
        access_request_collection.insert_one(access_request)

    # Save this for later
    pre_migration_docs = access_request_collection.find().to_list()

    await run_db_migrations(
        config=migration_config, target_version=2, migration_map={2: V2Migration}
    )

    # Verify V2 migration was applied correctly
    migrated_docs = access_request_collection.find().to_list()
    assert len(migrated_docs) == len(ACCESS_REQUESTS_V1)

    for doc in migrated_docs:
        assert "__metadata__" in doc
        assert doc["__metadata__"]["published"] == True
        assert not doc["__metadata__"]["deleted"]
        assert UUID(doc["__metadata__"]["correlation_id"])
        assert doc["dataset_title"] == ""
        assert doc["dac_alias"] == ""
        assert doc["dac_email"] == "helpdesk@ghga.de"
        for field in [
            "dataset_description",
            "ticket_id",
            "internal_note",
            "note_to_requester",
        ]:
            assert field in doc
            assert doc[field] == None

    # Reverse the V2 migration
    await run_db_migrations(
        config=migration_config, target_version=1, migration_map={2: V2Migration}
    )

    # Make sure contents now match beginning
    reverted_docs = access_request_collection.find().to_list()
    assert reverted_docs == pre_migration_docs


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
