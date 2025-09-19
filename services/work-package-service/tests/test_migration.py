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

"""Tests for the WPS database migrations."""

from asyncio import sleep
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from hexkit.providers.mongodb.testutils import MongoDbFixture
from hexkit.utils import now_utc_ms_prec

from tests.fixtures import fixture_config  # noqa: F401
from wps.core.models import WorkPackage, WorkPackageType
from wps.core.tokens import generate_work_package_access_token, hash_token
from wps.migrations import run_db_migrations

pytestmark = pytest.mark.asyncio()


async def test_migration_v2(config, mongodb: MongoDbFixture):
    """Test the migration to DB version 2 and reversion to DB version 1."""
    # Generate sample 'old' data that needs to be migrated
    data: list[dict[str, Any]] = []

    for i in range(3):
        old_work_package = WorkPackage(
            type=WorkPackageType.DOWNLOAD,
            files={},
            created=now_utc_ms_prec(),
            expires=now_utc_ms_prec(),
            id=uuid4(),
            dataset_id=f"GHGADataset{i}",
            user_id=uuid4(),
            full_user_name="Test User",
            email="test_user@some.org",
            user_public_crypt4gh_key="some-public-key",
            token_hash=hash_token(generate_work_package_access_token()),
        ).model_dump()

        # Convert data to the old format
        old_work_package["_id"] = str(old_work_package.pop("id"))
        old_work_package["user_id"] = str(old_work_package["user_id"])
        old_work_package["created"] = old_work_package["created"].isoformat()
        old_work_package["expires"] = old_work_package["expires"].isoformat()
        data.append(old_work_package)
        await sleep(0.1)  # sleep so timestamps are meaningfully different

    data.sort(key=lambda x: x["_id"])
    # Clear out anything so we definitely start with an empty collection
    db = mongodb.client[config.db_name]
    collection = db["workPackages"]
    collection.delete_many({})

    # Insert the test data
    collection.insert_many(data)

    # Run the migration
    await run_db_migrations(config=config, target_version=2)

    # Retrieve the migrated data and compare
    migrated_data = collection.find().to_list()
    migrated_data.sort(key=lambda x: x["_id"])

    assert len(migrated_data) == len(data)
    for old, new in zip(data, migrated_data, strict=True):
        assert str(new["_id"]) == old["_id"]
        assert str(new["user_id"]) == old["user_id"]

        new_created = new["created"]
        new_expires = new["expires"]

        # Make sure the migrated data has the right types
        assert isinstance(new["_id"], UUID)
        assert isinstance(new_created, datetime)
        assert isinstance(new_expires, datetime)

        # rather than calculating exact date mig results (tested in hexkit), just verify
        #  that it's within half a millisecond
        max_time_diff = timedelta(microseconds=500)
        assert abs(new_created - datetime.fromisoformat(old["created"])) < max_time_diff
        assert abs(new_expires - datetime.fromisoformat(old["expires"])) < max_time_diff

        assert new_created.microsecond % 1000 == 0
        assert new_expires.microsecond % 1000 == 0

    # now unapply (dates will not have microseconds of course)
    await run_db_migrations(config=config, target_version=1)
    reverted_data = collection.find().to_list()
    reverted_data.sort(key=lambda x: x["_id"])
    assert len(reverted_data) == len(data)
    for reverted, new in zip(reverted_data, migrated_data, strict=True):
        assert isinstance(reverted["_id"], str)
        assert isinstance(reverted["user_id"], str)
        assert isinstance(reverted["created"], str)
        assert isinstance(reverted["expires"], str)

        assert reverted["_id"] == str(new["_id"])
        assert reverted["user_id"] == str(new["user_id"])
        assert reverted["created"] == new["created"].isoformat()
        assert reverted["expires"] == new["expires"].isoformat()
