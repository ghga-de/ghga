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

import inspect

import pytest

from dlqs import main
from hexkit.providers.mongodb.migrations import (
    DbVersionMismatchError,
    check_db_version,
)
from hexkit.providers.mongodb.testutils import MongoDbFixture
from tests.fixtures.config import get_config

# Every coroutine in `main` is an entry point; `migrate_db` alone may change the version.
ENTRYPOINTS = sorted(
    name
    for name, obj in vars(main).items()
    if inspect.iscoroutinefunction(obj)
    and obj.__module__ == main.__name__
    and name != "migrate_db"
)


@pytest.fixture(autouse=True)
def empty_database(mongodb: MongoDbFixture):
    """Start each test on an empty database, as a fresh deployment does."""
    mongodb.empty_collections()


def test_entrypoints_found():
    """The introspection still finds the entry points."""
    assert ENTRYPOINTS, "No entry points found - has main.py been restructured?"


@pytest.mark.asyncio()
@pytest.mark.parametrize("entrypoint", ENTRYPOINTS)
async def test_entrypoint_refuses_unmigrated_db(
    entrypoint: str, mongodb: MongoDbFixture, monkeypatch: pytest.MonkeyPatch
):
    """An entry point stops before its work when the database is not migrated."""
    config = get_config(sources=[mongodb.config])
    monkeypatch.setattr(main, "Config", lambda: config)
    monkeypatch.setattr(main, "configure_logging", lambda config: None)
    with pytest.raises(DbVersionMismatchError):
        await getattr(main, entrypoint)()


@pytest.mark.asyncio()
async def test_migrate_db_reaches_db_version(
    mongodb: MongoDbFixture, monkeypatch: pytest.MonkeyPatch
):
    """`migrate_db` brings an empty database to the version the entry points check."""
    config = get_config(sources=[mongodb.config])
    monkeypatch.setattr(main, "Config", lambda: config)
    monkeypatch.setattr(main, "configure_logging", lambda config: None)
    await main.migrate_db()
    await check_db_version(config=config, target_version=main.DB_VERSION)
