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

"""Test that the entry points start only on a database at `DB_VERSION`."""

import pytest

from auth_service import main
from auth_service.config import Config
from hexkit.providers.mongodb.migrations import (
    DbVersionMismatchError,
    check_db_version,
)
from hexkit.providers.mongodb.testutils import MongoDbFixture

pytestmark = pytest.mark.asyncio()


@pytest.fixture(autouse=True)
def empty_database(mongodb: MongoDbFixture):
    """Start each test on an empty database, as a fresh deployment does."""
    mongodb.empty_collections()


@pytest.fixture(name="config")
def config_fixture(mongodb: MongoDbFixture, monkeypatch: pytest.MonkeyPatch) -> Config:
    """A service config on the test database, used by the entry points."""
    config = Config(
        mongo_dsn=mongodb.config.mongo_dsn,
        db_name=mongodb.config.db_name,
        kafka_servers=["kafka:9092"],
        service_instance_id="001",
        migration_wait_sec=2,
        db_version_collection="authDbVersions",
    )
    monkeypatch.setattr(main, "Config", lambda: config)
    monkeypatch.setattr(main, "configure_logging", lambda config: None)
    return config


@pytest.mark.parametrize("apis", [["ext_auth"], ["users"], ["claims", "access"]])
async def test_run_rest_app_refuses_unmigrated_db(
    config: Config, apis: list[str], monkeypatch: pytest.MonkeyPatch
):
    """The REST apps stop before their work when the database is not migrated."""
    config = config.model_copy(update={"provide_apis": apis})
    monkeypatch.setattr(main, "Config", lambda: config)
    with pytest.raises(DbVersionMismatchError):
        await main.run_rest_app()


async def test_consume_events_refuses_unmigrated_db(config: Config):
    """The consumer stops before its work when the database is not migrated."""
    with pytest.raises(DbVersionMismatchError):
        await main.consume_events(run_forever=False)


async def test_migrate_db_reaches_db_version(config: Config):
    """`migrate_db` brings an empty database to the version the entry points check."""
    await main.migrate_db()
    await check_db_version(config=config, target_version=main.DB_VERSION)
