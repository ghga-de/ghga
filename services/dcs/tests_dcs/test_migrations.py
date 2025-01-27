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

import math
from random import randint

import crypt4gh.lib
import pytest
from ghga_service_commons.utils.utc_dates import UTCDatetime, now_as_utc
from hexkit.providers.mongodb.provider import dto_to_document
from hexkit.providers.mongodb.testutils import MongoDbFixture
from pydantic import BaseModel

from dcs.core.models import AccessTimeDrsObject
from dcs.migration_logic._manager import MigrationStepError
from dcs.migrations import run_db_migrations
from tests_dcs.fixtures.config import get_config


def calc_encrypted_size(decrypted_size: int) -> int:
    """Calculate the encrypted size given the decrypted object's size."""
    num_segments = math.ceil(decrypted_size / crypt4gh.lib.SEGMENT_SIZE)
    return decrypted_size + num_segments * 28


@pytest.mark.asyncio
async def test_v2_migration(
    mongodb: MongoDbFixture,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test the migration script for v2 where we add the size of the encrypted object
    to the docs in the drs_objects collection.
    """
    # Patch the config
    config = get_config(sources=[mongodb.config])
    client = mongodb.client
    coll = client[config.db_name]["drs_objects"]

    # Set up test data - we want some random object sizes to verify we're not accidentally
    #  reading some dummy value somewhere. Record the sizes so we can check later that
    #  what we retrieve is correct.
    test_data_sizes: dict[str, list[int]] = {}
    base_model = AccessTimeDrsObject(
        file_id="",
        decryption_secret_id="",
        decrypted_sha256="",
        decrypted_size=0,
        creation_date=now_as_utc().isoformat(),
        s3_endpoint_alias="HD01",
        object_id="",
        last_accessed=now_as_utc(),
        encrypted_size=0,
    )

    for n in range(1, 10):
        drs_object = dto_to_document(base_model, id_field="file_id")
        drs_object.pop("encrypted_size")
        base_size = 10**7
        multiplier = randint(1, 8000)
        decrypted_size = base_size * multiplier
        encrypted_size = calc_encrypted_size(decrypted_size)
        drs_object["_id"] = f"examplefile00{n}"
        test_data_sizes[drs_object["_id"]] = [decrypted_size, encrypted_size]
        drs_object["object_id"] = f"objectid00{n}"
        drs_object["decrypted_size"] = decrypted_size
        coll.insert_one(drs_object)

    post_insert = coll.find().to_list()
    assert len(post_insert) == 9
    for doc in post_insert:
        assert doc["decrypted_size"] == test_data_sizes[doc["_id"]][0]
        assert "encrypted_size" not in doc

    # Run the database migrations, which should create the lock/versioning collection
    #  and then update the 'file_metadata' collection.
    await run_db_migrations(config=config)

    # Make sure the docs from file_metadata were updated with the right size values
    post_apply = coll.find().to_list()
    assert len(post_apply) == 9
    for doc in post_apply:
        assert doc["decrypted_size"] == test_data_sizes[doc["_id"]][0]
        assert "encrypted_size" in doc
        assert doc["encrypted_size"] == test_data_sizes[doc["_id"]][1]

    # Unapply the v2 migration, which will fail because the current model requires
    #  the `encrypted_size` field.
    with pytest.raises(MigrationStepError):
        await run_db_migrations(config=config, target_version=1)

    # Make sure the docs from file_metadata were updated with the right size values
    post_failed_unapply = coll.find().to_list()
    assert len(post_failed_unapply) == 9
    for doc in post_failed_unapply:
        assert "encrypted_size" in doc
        assert doc["encrypted_size"] == test_data_sizes[doc["_id"]][1]

    # Monkeypatch the pydantic model to resemble the old version so we can test reversal
    class PatchedDrsModel(BaseModel):
        """Does not contain the encrypted_size field"""

        file_id: str
        decryption_secret_id: str
        decrypted_sha256: str
        decrypted_size: int
        creation_date: str
        s3_endpoint_alias: str
        object_id: str
        last_accessed: UTCDatetime

    monkeypatch.setattr(
        "dcs.migration_logic.dcs_migrations.AccessTimeDrsObject", PatchedDrsModel
    )
    await run_db_migrations(config=config, target_version=1)

    post_unapply = coll.find().to_list()
    assert len(post_unapply) == 9
    for doc in post_unapply:
        assert "encrypted_size" not in doc


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
