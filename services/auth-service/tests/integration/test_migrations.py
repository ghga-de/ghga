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

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from hexkit.providers.mongodb.testutils import MongoDbFixture

from auth_service.config import Config
from auth_service.migrations.entry import run_db_migrations

pytestmark = pytest.mark.asyncio()

old_date1 = datetime(2025, 8, 10, 10, 10, 59, 234789, tzinfo=UTC).isoformat()
migrated_date1 = datetime(2025, 8, 10, 10, 10, 59, 235000, tzinfo=UTC)
reverted_date1 = datetime(2025, 8, 10, 10, 10, 59, 235000, tzinfo=UTC).isoformat()

old_date2 = datetime(2026, 8, 10, 10, 10, 59, 234789, tzinfo=UTC).isoformat()
migrated_date2 = datetime(2026, 8, 10, 10, 10, 59, 235000, tzinfo=UTC)
reverted_date2 = datetime(2026, 8, 10, 10, 10, 59, 235000, tzinfo=UTC).isoformat()


def produce_claim_docs_for_v2_mig() -> dict[str, list[dict[str, Any]]]:
    """Produce old, migrated, and reverted claims docs for testing the migration to v2"""
    doc1 = {  # iva_id populated, revocation_date not populated
        "_id": "da503041-b0e5-479e-bce2-1d94863c1969",
        "valid_from": old_date1,
        "valid_until": old_date2,
        "iva_id": "1193b5bb-5a6e-4df9-829e-0fbac21a2ea4",
        "visa_type": "https://www.ghga.de/GA4GH/VisaTypes/Role/v1.0",
        "visa_value": "data_steward@ghga.de",
        "assertion_date": old_date1,
        "source": "https://ghga.de",
        "sub_source": None,
        "asserted_by": "system",
        "conditions": None,
        "user_id": "70411a11-d961-4050-85ec-d35a1acd6ec3",
        "creation_date": old_date1,
        "revocation_date": None,
    }
    migrated_doc1: dict[str, Any] = deepcopy(doc1)
    migrated_doc1["_id"] = UUID("da503041-b0e5-479e-bce2-1d94863c1969")
    migrated_doc1["valid_from"] = migrated_date1
    migrated_doc1["valid_until"] = migrated_date2
    migrated_doc1["iva_id"] = UUID("1193b5bb-5a6e-4df9-829e-0fbac21a2ea4")
    migrated_doc1["assertion_date"] = migrated_date1
    migrated_doc1["user_id"] = UUID("70411a11-d961-4050-85ec-d35a1acd6ec3")
    migrated_doc1["creation_date"] = migrated_date1

    reverted_doc1 = deepcopy(doc1)
    reverted_doc1["valid_from"] = reverted_date1
    reverted_doc1["valid_until"] = reverted_date2
    reverted_doc1["assertion_date"] = reverted_date1
    reverted_doc1["creation_date"] = reverted_date1

    doc2 = {  # no iva_id, but has revocation date populated
        "_id": "fc112ec9-2adb-4081-985c-7731f863b65e",
        "valid_from": old_date1,
        "valid_until": old_date2,
        "iva_id": None,
        "visa_type": "https://www.ghga.de/GA4GH/VisaTypes/Role/v1.0",
        "visa_value": "data_steward@ghga.de",
        "assertion_date": old_date1,
        "source": "https://ghga.de",
        "sub_source": None,
        "asserted_by": "system",
        "conditions": None,
        "user_id": "70411a11-d961-4050-85ec-d35a1acd6ec3",
        "creation_date": old_date1,
        "revocation_date": old_date1,
    }
    migrated_doc2: dict[str, Any] = deepcopy(doc2)
    migrated_doc2["_id"] = UUID("fc112ec9-2adb-4081-985c-7731f863b65e")
    migrated_doc2["valid_from"] = migrated_date1
    migrated_doc2["valid_until"] = migrated_date2
    migrated_doc2["assertion_date"] = migrated_date1
    migrated_doc2["user_id"] = UUID("70411a11-d961-4050-85ec-d35a1acd6ec3")
    migrated_doc2["creation_date"] = migrated_date1
    migrated_doc2["revocation_date"] = migrated_date1

    reverted_doc2 = deepcopy(doc2)
    reverted_doc2["valid_from"] = reverted_date1
    reverted_doc2["valid_until"] = reverted_date2
    reverted_doc2["assertion_date"] = reverted_date1
    reverted_doc2["creation_date"] = reverted_date1
    reverted_doc2["revocation_date"] = reverted_date1

    return {
        "old": [doc1, doc2],
        "expected_migrated": [migrated_doc1, migrated_doc2],
        "expected_reverted": [reverted_doc1, reverted_doc2],
    }


def produce_iva_docs_for_v2_mig() -> dict[str, list[dict[str, Any]]]:
    """Produce old, migrated, and reverted iva docs for testing the migration to v2"""
    doc1: dict[str, Any] = {
        "_id": "be2d895d-1ca6-4369-a893-25efcf6b0a5f",
        "created": old_date1,
        "changed": old_date2,
        "user_id": "9cd6d9ee-b30b-4816-a234-9b03b60f7df3",
        "verification_code_hash": None,
        "verification_attempts": 0,
        "type": "InPerson",
        "value": "GHGA",
        "state": "Unverified",
        "__metadata__": {
            "deleted": False,
            "published": False,
            "correlation_id": "e3bfdf8f-a30b-4321-804e-5f35f6958dd2",
        },
    }
    migrated_doc1 = deepcopy(doc1)
    migrated_doc1["_id"] = UUID("be2d895d-1ca6-4369-a893-25efcf6b0a5f")
    migrated_doc1["created"] = migrated_date1
    migrated_doc1["changed"] = migrated_date2
    migrated_doc1["user_id"] = UUID("9cd6d9ee-b30b-4816-a234-9b03b60f7df3")
    migrated_doc1["__metadata__"]["correlation_id"] = UUID(
        "e3bfdf8f-a30b-4321-804e-5f35f6958dd2"
    )
    reverted_doc1 = deepcopy(doc1)
    reverted_doc1["created"] = reverted_date1
    reverted_doc1["changed"] = reverted_date2

    doc2: dict[str, Any] = {
        "_id": "c589bf1d-150a-49a0-adb7-599525249ff0",
        "__metadata__": {
            "deleted": True,
            "published": False,
            "correlation_id": "83f074de-05a9-45e8-b025-c0cefe369ec9",
        },
    }
    migrated_doc2 = deepcopy(doc2)
    migrated_doc2["_id"] = UUID("c589bf1d-150a-49a0-adb7-599525249ff0")
    migrated_doc2["__metadata__"]["correlation_id"] = UUID(
        "83f074de-05a9-45e8-b025-c0cefe369ec9"
    )
    reverted_doc2 = deepcopy(doc2)

    doc3: dict[str, Any] = {
        "_id": "f4969771-630d-4c9b-b80d-a7ad69570e9b",
        "created": old_date1,
        "changed": old_date2,
        "user_id": "587d7f49-b6ae-42d4-a163-58899b38915b",
        "verification_code_hash": None,
        "verification_attempts": 0,
        "type": "InPerson",
        "value": "GHGA",
        "state": "Unverified",
        "__metadata__": {
            "deleted": False,
            "published": False,
            "correlation_id": "3b4113a0-975a-486c-a37e-8cc0d7cc48a3",
        },
    }
    migrated_doc3 = deepcopy(doc3)
    migrated_doc3["_id"] = UUID("f4969771-630d-4c9b-b80d-a7ad69570e9b")
    migrated_doc3["created"] = migrated_date1
    migrated_doc3["changed"] = migrated_date2
    migrated_doc3["user_id"] = UUID("587d7f49-b6ae-42d4-a163-58899b38915b")
    migrated_doc3["__metadata__"]["correlation_id"] = UUID(
        "3b4113a0-975a-486c-a37e-8cc0d7cc48a3"
    )
    reverted_doc3 = deepcopy(doc3)
    reverted_doc3["created"] = reverted_date1
    reverted_doc3["changed"] = reverted_date2

    return {
        "old": [doc1, doc2, doc3],
        "expected_migrated": [migrated_doc1, migrated_doc2, migrated_doc3],
        "expected_reverted": [reverted_doc1, reverted_doc2, reverted_doc3],
    }


def produce_user_token_docs_for_v2_mig() -> dict[str, list[dict[str, Any]]]:
    """Produce old, migrated, and reverted user token docs for testing the migration to v2"""
    doc1: dict[str, Any] = {
        "_id": "ed6fbad0-bd88-4fc7-be6a-766f86f69e33",
        "totp_token": {
            "encrypted_secret": "gibberish",
            "last_counter": 123123,
            "counter_attempts": 1,
            "total_attempts": 2,
        },
    }
    migrated_doc1 = deepcopy(doc1)
    migrated_doc1["_id"] = UUID("ed6fbad0-bd88-4fc7-be6a-766f86f69e33")
    reverted_doc1 = deepcopy(doc1)

    doc2: dict[str, Any] = {
        "_id": "f401b1cc-daaf-42c7-857a-621436855dab",
        "totp_token": {
            "encrypted_secret": "gibberish",
            "last_counter": 123123,
            "counter_attempts": 1,
            "total_attempts": 2,
        },
    }
    migrated_doc2 = deepcopy(doc2)
    migrated_doc2["_id"] = UUID("f401b1cc-daaf-42c7-857a-621436855dab")
    reverted_doc2 = deepcopy(doc2)

    return {
        "old": [doc1, doc2],
        "expected_migrated": [migrated_doc1, migrated_doc2],
        "expected_reverted": [reverted_doc1, reverted_doc2],
    }


def produce_user_docs_for_v2_mig() -> dict[str, list[dict[str, Any]]]:
    """Produce old, migrated, and reverted user docs for testing the migration to v2"""
    doc1: dict[str, Any] = {  # no status change
        "_id": "1c8838f6-2413-4186-81f4-0a98c8fffe1f",
        "registration_date": old_date1,
        "status_change": None,
        "active_submissions": [],
        "active_access_requests": [],
        "name": "James Doe",
        "title": "Dr.",
        "email": "test@test.com",
        "ext_id": "james@aai.org",
        "status": "active",
        "__metadata__": {
            "deleted": False,
            "published": True,
            "correlation_id": "0d94d065-4427-424d-8875-e95946a7079a",
        },
    }
    migrated_doc1 = deepcopy(doc1)
    migrated_doc1["_id"] = UUID("1c8838f6-2413-4186-81f4-0a98c8fffe1f")
    migrated_doc1["registration_date"] = migrated_date1
    migrated_doc1["__metadata__"]["correlation_id"] = UUID(
        "0d94d065-4427-424d-8875-e95946a7079a"
    )
    reverted_doc1 = deepcopy(doc1)
    reverted_doc1["registration_date"] = reverted_date1

    doc2: dict[str, Any] = {  # status change is populated
        "_id": "785c88b0-9ff9-42c8-83c5-bb3bdba10b2c",
        "registration_date": old_date1,
        "status_change": {
            "previous": "active",
            "by": "ff6b396d-c8aa-4f18-a3fe-ee354a1250e6",
            "context": "Too many failed TOTP login attempts",
            "change_date": old_date2,
        },
        "active_submissions": [],
        "active_access_requests": [],
        "name": "John Doe",
        "title": None,
        "email": "example@test.com",
        "ext_id": "john@aai.org",
        "status": "active",
        "__metadata__": {
            "deleted": False,
            "published": True,
            "correlation_id": "c3aa721c-cb77-4447-b74e-8df2ef5fa543",
        },
    }
    migrated_doc2 = deepcopy(doc2)
    migrated_doc2["_id"] = UUID("785c88b0-9ff9-42c8-83c5-bb3bdba10b2c")
    migrated_doc2["registration_date"] = migrated_date1
    migrated_doc2["status_change"]["by"] = UUID("ff6b396d-c8aa-4f18-a3fe-ee354a1250e6")
    migrated_doc2["status_change"]["change_date"] = migrated_date2
    migrated_doc2["__metadata__"]["correlation_id"] = UUID(
        "c3aa721c-cb77-4447-b74e-8df2ef5fa543"
    )
    reverted_doc2 = deepcopy(doc2)
    reverted_doc2["registration_date"] = reverted_date1
    reverted_doc2["status_change"]["change_date"] = reverted_date2

    doc3: dict[str, Any] = {
        "_id": "9abe34c3-3ee5-4e06-a87a-45001460c667",
        "__metadata__": {
            "deleted": True,
            "published": True,
            "correlation_id": "7ee3a091-1db1-44a8-aebe-a4552b173dfd",
        },
    }

    migrated_doc3 = deepcopy(doc3)
    migrated_doc3["_id"] = UUID("9abe34c3-3ee5-4e06-a87a-45001460c667")
    migrated_doc3["__metadata__"]["correlation_id"] = UUID(
        "7ee3a091-1db1-44a8-aebe-a4552b173dfd"
    )
    reverted_doc3 = deepcopy(doc3)

    return {
        "old": [doc1, doc2, doc3],
        "expected_migrated": [migrated_doc1, migrated_doc2, migrated_doc3],
        "expected_reverted": [reverted_doc1, reverted_doc2, reverted_doc3],
    }


async def test_v2_migration(mongodb: MongoDbFixture):
    """Test the apply and unapply functions of the v2 migration"""
    config = Config(
        mongo_dsn=mongodb.config.mongo_dsn,
        db_name=mongodb.config.db_name,
        kafka_servers=["kafka:9092"],
        service_instance_id="001",
        migration_wait_sec=2,
        db_version_collection="authDbVersions",
        claims_collection="claims",
        ivas_collection="ivas",
        user_tokens_collection="user_tokens",
        users_collection="users",
    )

    # clear anything that might be in the DB
    client = mongodb.client
    db = client[config.db_name]
    claims_collection = db[config.claims_collection]
    claims_collection.delete_many({})
    ivas_collection = db[config.ivas_collection]
    ivas_collection.delete_many({})
    user_tokens_collection = db[config.user_tokens_collection]
    user_tokens_collection.delete_many({})
    users_collection = db[config.users_collection]
    users_collection.delete_many({})

    # generate and insert data
    claims_data = produce_claim_docs_for_v2_mig()
    claims_collection.insert_many(claims_data["old"])
    ivas_data = produce_iva_docs_for_v2_mig()
    ivas_collection.insert_many(ivas_data["old"])
    user_tokens_data = produce_user_token_docs_for_v2_mig()
    user_tokens_collection.insert_many(user_tokens_data["old"])
    users_data = produce_user_docs_for_v2_mig()
    users_collection.insert_many(users_data["old"])

    # run migration
    await run_db_migrations(config=config, target_version=2)

    # check results
    migrated_claims = claims_collection.find({}).sort("_id").to_list()
    assert migrated_claims == claims_data["expected_migrated"]

    migrated_ivas = ivas_collection.find({}).sort("_id").to_list()
    assert migrated_ivas == ivas_data["expected_migrated"]

    migrated_user_tokens = user_tokens_collection.find({}).sort("_id").to_list()
    assert migrated_user_tokens == user_tokens_data["expected_migrated"]

    migrated_users = users_collection.find({}).sort("_id").to_list()
    assert migrated_users == users_data["expected_migrated"]

    # revert migration
    await run_db_migrations(config=config, target_version=1)
    # check results
    reverted_claims = claims_collection.find({}).sort("_id").to_list()
    assert reverted_claims == claims_data["expected_reverted"]

    reverted_ivas = ivas_collection.find({}).sort("_id").to_list()
    assert reverted_ivas == ivas_data["expected_reverted"]

    reverted_user_tokens = user_tokens_collection.find({}).sort("_id").to_list()
    assert reverted_user_tokens == user_tokens_data["expected_reverted"]

    reverted_users = users_collection.find({}).sort("_id").to_list()
    assert reverted_users == users_data["expected_reverted"]
