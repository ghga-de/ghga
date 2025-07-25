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

"""Tests for NOS DB migrations."""

import json
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from ghga_event_schemas.pydantic_ import AccessRequestDetails, User
from hexkit.providers.mongodb.testutils import MongoDbFixture

from nos.migrations import run_db_migrations
from tests.fixtures.config import get_config
from tests.fixtures.utils import make_access_request

pytestmark = pytest.mark.asyncio()


async def test_migration_v2(mongodb: MongoDbFixture):
    """Test the migration to DB version 2 and reversion to DB version 1."""
    config = get_config(sources=[mongodb.config])

    # Generate User and Access Request Details objects
    access_requests: list[AccessRequestDetails] = sorted(
        [make_access_request(user_id=uuid4()) for _ in range(3)], key=lambda x: x.id
    )
    users: list[User] = sorted(
        [
            User(user_id=uuid4(), name=f"User {i}", email=f"test{i}@test.com")
            for i in range(3)
        ],
        key=lambda x: x.user_id,
    )

    db = mongodb.client[config.db_name]
    ar_collection = db["accessRequests"]
    users_collection = db["users"]

    # Clear out anything so we definitely start with an empty collection
    ar_collection.delete_many({})
    users_collection.delete_many({})

    # Perform old serialization that used to be in hexkit pre-v6 and insert
    for ar in access_requests:
        document = json.loads(ar.model_dump_json())
        document["_id"] = document.pop("id")
        assert isinstance(document["_id"], str)
        assert isinstance(document["user_id"], str)
        assert isinstance(document["access_starts"], str)
        assert isinstance(document["access_ends"], str)
        ar_collection.insert_one(document)

    for user in users:
        document = json.loads(user.model_dump_json())
        document["_id"] = document.pop("user_id")
        assert isinstance(document["_id"], str)
        users_collection.insert_one(document)

    # Run the migration
    await run_db_migrations(config=config, target_version=2)

    # Retrieve the migrated data and compare
    migrated_access_requests = ar_collection.find().to_list()
    migrated_users = users_collection.find().to_list()

    assert len(migrated_access_requests) == len(access_requests)
    assert len(migrated_users) == len(users)

    for ar, migrated_ar in zip(access_requests, migrated_access_requests, strict=True):
        assert isinstance(migrated_ar["_id"], UUID)
        assert isinstance(migrated_ar["user_id"], UUID)
        assert migrated_ar["_id"] == ar.id
        assert migrated_ar["user_id"] == ar.user_id
        assert isinstance(migrated_ar["access_starts"], datetime)
        assert isinstance(migrated_ar["access_ends"], datetime)
        assert migrated_ar["access_starts"] == ar.access_starts
        assert migrated_ar["access_ends"] == ar.access_ends

    for user, migrated_user in zip(users, migrated_users, strict=True):
        assert isinstance(migrated_user["_id"], UUID)
        assert migrated_user["_id"] == user.user_id
        assert migrated_user["name"] == user.name
        assert migrated_user["email"] == user.email

    # Run the migration in reverse
    await run_db_migrations(config=config, target_version=1)

    reversed_access_requests = sorted(
        ar_collection.find().to_list(), key=lambda x: x["_id"]
    )
    reversed_users = sorted(users_collection.find().to_list(), key=lambda x: x["_id"])
    assert len(reversed_access_requests) == len(access_requests)
    assert len(reversed_users) == len(users)

    # Make sure access requests now have isoformat string dates and string UUIDs
    for ar, reversed_ar in zip(access_requests, reversed_access_requests, strict=True):
        assert isinstance(reversed_ar["_id"], str)
        assert isinstance(reversed_ar["user_id"], str)
        assert reversed_ar["_id"] == str(ar.id)
        assert reversed_ar["user_id"] == str(ar.user_id)
        assert isinstance(reversed_ar["access_starts"], str)
        assert isinstance(reversed_ar["access_ends"], str)
        assert reversed_ar["access_starts"] == ar.access_starts.isoformat()
        assert reversed_ar["access_ends"] == ar.access_ends.isoformat()

    # Make sure users now have string UUIDs
    for user, reversed_user in zip(users, reversed_users, strict=True):
        assert isinstance(reversed_user["_id"], str)
        assert reversed_user["_id"] == str(user.user_id)
        assert reversed_user["name"] == user.name
        assert reversed_user["email"] == user.email
