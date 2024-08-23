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
"""Test mongodb state management."""

import pytest
from hexkit.providers.mongodb.testutils import MongoDbFixture

from sms.adapters.outbound.docs_dao import DEFAULT_DBS, DocsDao
from sms.models import DocumentType
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio()

TESTDB = "testdb"
ALLOPS = "allops"


async def test_all_ops(mongodb: MongoDbFixture):
    """Test get, upsert, and delete methods on the docs dao."""
    config = get_config(sources=[mongodb.config])

    # Verify the db is empty
    async with DocsDao(config=config) as docs_dao:
        with pytest.raises(DocsDao.DbNotFoundError):
            await docs_dao.get(db_name=TESTDB, collection=ALLOPS, criteria={})

        # Insert docs
        docs_to_insert: list[DocumentType] = [
            {"_id": "1", "test": "test"},
            {"_id": "2", "test": "second"},
            {"_id": "3", "test": "third"},
        ]
        await docs_dao.upsert(
            db_name=TESTDB,
            collection=ALLOPS,
            id_field="_id",
            documents=docs_to_insert,
        )

        # Check that docs are there
        post_insert = await docs_dao.get(db_name=TESTDB, collection=ALLOPS, criteria={})
        assert post_insert == docs_to_insert

        # Update docs
        doc_to_update = {"_id": "1", "test": "updated"}
        await docs_dao.upsert(
            db_name=TESTDB,
            collection=ALLOPS,
            id_field="_id",
            documents=[doc_to_update],
        )

        # Check that docs are updated
        post_update = await docs_dao.get(db_name=TESTDB, collection=ALLOPS, criteria={})
        docs_to_insert[0] = doc_to_update
        assert post_update == docs_to_insert

        # Delete first doc
        await docs_dao.delete(db_name=TESTDB, collection=ALLOPS, criteria={"_id": "3"})
        docs_to_insert.pop()

        # Check that other docs still remain
        remaining = await docs_dao.get(db_name=TESTDB, collection=ALLOPS, criteria={})
        assert remaining == docs_to_insert

        # Delete all docs
        await docs_dao.delete(db_name=TESTDB, collection=ALLOPS, criteria={})
        assert not await docs_dao.get(db_name=TESTDB, collection=ALLOPS, criteria={})


@pytest.mark.parametrize(
    "prefix, db_name_arg, expected",
    [
        ("db", "", {}),
        ("", "", {"test_db1": ["test", "test2"], "test_db2": ["test1"]}),
        (None, "", {"db1": ["test", "test2"], "db2": ["test1"]}),
        (None, "db1", {"db1": ["test", "test2"]}),
        (None, "nonexistent", {"nonexistent": []}),
        ("", "test_db1", {"test_db1": ["test", "test2"]}),
    ],
)
async def test_get_db_map_for_prefix(
    mongodb: MongoDbFixture,
    prefix: str | None,
    db_name_arg: str,
    expected: dict[str, list[str]],
):
    """Test get_db_map_for_prefix method on the docs dao."""
    config = get_config(sources=[mongodb.config])
    if prefix is None:
        prefix = config.db_prefix

    db_name1 = "db1"
    db_name2 = "db2"
    db_map_prefix_set = {db_name1: ["test", "test2"], db_name2: ["test1"]}

    async with DocsDao(config=config) as docs_dao:
        # MongoDbFixture reset only empties collections, it doesn't delete them
        # so we need to drop the databases manually to verify the functionality
        for db in await docs_dao._client.list_database_names():
            if db not in DEFAULT_DBS:
                await docs_dao._client.drop_database(db)

        # Insert documents to create the expected db_map
        for db_name, colls in db_map_prefix_set.items():
            for coll in colls:
                await docs_dao._client[f"{config.db_prefix}{db_name}"][coll].insert_one(
                    {"key": "value"}
                )

        results = await docs_dao.get_db_map_for_prefix(
            prefix=prefix, db_name=db_name_arg
        )
        assert results == expected


async def test_deletion_on_nonexistent_resources(mongodb: MongoDbFixture):
    """Test delete method on nonexistent dbs, collections.

    There should not be any error raised.
    """
    config = get_config(sources=[mongodb.config])

    async with DocsDao(config=config) as docs_dao:
        await docs_dao._client["exists"]["exists"].insert_one({"key": "value"})
        # Delete nonexistent db contents
        await docs_dao.delete(
            db_name="nonexistent", collection="nonexistent", criteria={}
        )

        # Delete nonexistent collection contents
        await docs_dao.delete(db_name="exists", collection="nonexistent", criteria={})
