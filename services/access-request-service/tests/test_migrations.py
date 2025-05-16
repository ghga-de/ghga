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

from uuid import UUID

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
