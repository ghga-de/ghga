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

"""Test the DocDao class without any real"""

from contextlib import nullcontext
from unittest.mock import AsyncMock, call

import pytest
from hexkit.providers.mongodb.testutils import MongoDbFixture

from sms.core.docs_handler import DocsHandler, Permissions
from sms.inject import prepare_docs_handler
from sms.models import Criteria, DocumentType, UpsertionDetails
from sms.ports.outbound.docs_dao import DocsDaoPort
from tests.fixtures.config import get_config

TEST_DOCS: list[DocumentType] = [
    {"_id": "1", "test": "test"},
    {"_id": "2", "test": "second"},
]

READONLY = "readonly"
WRITEONLY = "writeonly"
READWRITE = "readwrite"
ALLOPS = "allops"
UNLISTED_COLLECTION = "unlistedcollection"
UNLISTED_DB = "unlisteddb"
TEST_DB = "testdb"


@pytest.mark.parametrize(
    "query_params, expected_results",
    [
        ({}, {}),
        ({"plain": "value"}, {"plain": "value"}),
        ({"nested": '{"str": "45"}'}, {"nested": {"str": "45"}}),
        ({"nested": '{"num": 45}'}, {"nested": {"num": 45}}),
        (
            {"outer": '{"inner": {"str": "45"}}'},
            {"outer": {"inner": {"str": "45"}}},
        ),
    ],
    ids=["empty", "plain", "nested_str", "nested_num", "double_nested"],
)
def test_parse_criteria(query_params: Criteria, expected_results: Criteria):
    """Test the parse_criteria method."""
    docs_handler = DocsHandler(config=get_config(), docs_dao=AsyncMock())
    parsed_criteria = docs_handler._parse_criteria(query_params)
    assert parsed_criteria == expected_results


@pytest.mark.parametrize(
    "query_params",
    [
        {"key": "{str: 45}"},
        {"key": '{"str": test}'},
        {"key": "extra", "problem": '{"outer": {"inner": "center"}'},
    ],
    ids=["key_missing_quotes", "value_missing_quotes", "missing_brackets"],
)
def test_criteria_format_error(query_params: Criteria):
    """Test the CriteriaFormatError class."""
    with pytest.raises(DocsHandler.CriteriaFormatError):
        docs_handler = DocsHandler(config=get_config(), docs_dao=AsyncMock())
        docs_handler._parse_criteria(query_params)


def test_permissions():
    """Test the Permissions class."""
    config = get_config()
    permissions = Permissions(config.db_permissions)

    assert permissions.get_permissions(TEST_DB, ALLOPS) == "rw"
    assert permissions.get_permissions(TEST_DB, READONLY) == "r"
    assert permissions.get_permissions(TEST_DB, WRITEONLY) == "w"
    assert permissions.get_permissions(TEST_DB, READWRITE) == "rw"
    assert permissions.get_permissions(TEST_DB, UNLISTED_COLLECTION) == ""
    assert permissions.get_permissions(UNLISTED_DB, "all") == ""
    assert Permissions([]).get_permissions(TEST_DB, ALLOPS) == ""


@pytest.mark.parametrize(
    "db_name, collection, error",
    [
        (TEST_DB, UNLISTED_COLLECTION, PermissionError),
        (TEST_DB, WRITEONLY, PermissionError),
        (TEST_DB, READONLY, None),
        (TEST_DB, READWRITE, None),
        (TEST_DB, ALLOPS, None),
        (UNLISTED_DB, "all", PermissionError),
    ],
)
@pytest.mark.asyncio
async def test_read(
    mongodb: MongoDbFixture,
    db_name: str,
    collection: str,
    error: type[Exception] | None,
):
    """Make sure we get a permission error when trying to read a write-only collection."""
    config = get_config(sources=[mongodb.config])

    async with prepare_docs_handler(config=config) as docs_handler:
        # Attempt read
        with pytest.raises(error) if error else nullcontext():
            await docs_handler.get(db_name=db_name, collection=collection, criteria={})


@pytest.mark.parametrize(
    "db_name, collection, error",
    [
        (TEST_DB, UNLISTED_COLLECTION, PermissionError),
        (TEST_DB, WRITEONLY, None),
        (TEST_DB, READONLY, PermissionError),
        (TEST_DB, READWRITE, None),
        (TEST_DB, ALLOPS, None),
        (UNLISTED_DB, "all", PermissionError),
    ],
    ids=[
        "UnlistedCollection",
        "WriteOnlyCollection",
        "ReadOnlyCollection",
        "ReadWriteCollection",
        "AllOpsCollection",
        "UnlistedDB",
    ],
)
@pytest.mark.asyncio
async def test_write(
    mongodb: MongoDbFixture,
    db_name: str,
    collection: str,
    error: type[Exception] | None,
):
    """Make sure we get a permission error when trying to write to a read-only collection."""
    config = get_config(sources=[mongodb.config])

    upsertion_details = UpsertionDetails(documents=TEST_DOCS)
    async with prepare_docs_handler(config=config) as docs_handler:
        with pytest.raises(error) if error else nullcontext():
            # Attempt upsert
            await docs_handler.upsert(
                db_name=db_name,
                collection=collection,
                upsertion_details=upsertion_details,
            )

        with pytest.raises(error) if error else nullcontext():
            # Attempt delete
            await docs_handler.delete(
                db_name=db_name,
                collection=collection,
                criteria={},
            )


@pytest.mark.asyncio
async def test_dao_error_handling():
    """Test errors that bubble up from the DocsDao. Currently they are not handled."""
    docs_dao = AsyncMock(spec=DocsDaoPort)
    docs_dao.get.side_effect = DocsHandler.OperationError()
    docs_dao.upsert.side_effect = DocsHandler.OperationError()
    docs_dao.delete.side_effect = DocsHandler.OperationError()

    config = get_config()
    docs_handler = DocsHandler(config=config, docs_dao=docs_dao)
    with pytest.raises(DocsHandler.OperationError):
        await docs_handler.get(db_name=TEST_DB, collection=ALLOPS, criteria={})

    with pytest.raises(DocsHandler.OperationError):
        await docs_handler.upsert(
            db_name=TEST_DB,
            collection=ALLOPS,
            upsertion_details=UpsertionDetails(documents=TEST_DOCS),
        )

    with pytest.raises(DocsHandler.OperationError):
        await docs_handler.delete(db_name=TEST_DB, collection=ALLOPS, criteria={})


@pytest.mark.asyncio
async def test_prefix_handling_wrt_permissions():
    """Test that the prefix is correctly handled."""
    # Make sure the db_prefix is not empty
    config = get_config()
    assert config.db_prefix
    docs_handler = DocsHandler(config=config, docs_dao=AsyncMock())

    # Query the readwrite collection with the prefix included (meaning the docs_handler
    # will look for test_test_testdb.readwrite instead of just test_testdb.readwrite)
    full_name = f"{config.db_prefix}{TEST_DB}"
    with pytest.raises(PermissionError):
        await docs_handler.get(db_name=full_name, collection=READWRITE, criteria={})

    with pytest.raises(PermissionError):
        await docs_handler.upsert(
            db_name=full_name,
            collection=READWRITE,
            upsertion_details=UpsertionDetails(documents=TEST_DOCS),
        )

    with pytest.raises(PermissionError):
        await docs_handler.delete(db_name=full_name, collection=READWRITE, criteria={})

    # Make sure performing the same operations without the prefix works fine
    await docs_handler.get(db_name=TEST_DB, collection=ALLOPS, criteria={})
    await docs_handler.upsert(
        db_name=TEST_DB,
        collection=ALLOPS,
        upsertion_details=UpsertionDetails(documents=TEST_DOCS),
    )
    await docs_handler.delete(db_name=TEST_DB, collection=ALLOPS, criteria={})


@pytest.mark.asyncio
async def test_wildcard_deletion():
    """Test deletion with wildcard arguments."""
    docs_dao = AsyncMock(spec=DocsDaoPort)
    docs_dao.delete = AsyncMock()
    config = get_config()
    docs_handler = DocsHandler(config=config, docs_dao=docs_dao)

    # Test the invalid case of deleting a specific collection in all databases
    with pytest.raises(ValueError):
        await docs_handler.delete(db_name="*", collection=ALLOPS, criteria={})
    docs_dao.delete.assert_not_awaited()
    docs_dao.delete.reset_mock()

    # Delete all collections in all databases that have write permissions
    docs_dao.get_db_map_for_prefix.return_value = {
        TEST_DB: [ALLOPS, READONLY, WRITEONLY],
        "testdb2": [WRITEONLY],
        "testdb3": [READONLY],
    }
    await docs_handler.delete(db_name="*", collection="*", criteria={})
    assert docs_dao.delete.call_args_list == [
        call(db_name=f"{config.db_prefix}{TEST_DB}", collection=ALLOPS, criteria={}),
        call(db_name=f"{config.db_prefix}{TEST_DB}", collection=WRITEONLY, criteria={}),
        call(db_name=f"{config.db_prefix}testdb2", collection=WRITEONLY, criteria={}),
    ]

    docs_dao.delete.reset_mock()

    # Delete all collections in the testdb that have write permissions
    docs_dao.get_db_map_for_prefix.return_value = {
        TEST_DB: [ALLOPS, READONLY, WRITEONLY],
    }
    await docs_handler.delete(db_name=TEST_DB, collection="*", criteria={})
    assert docs_dao.delete.call_args_list == [
        call(db_name=f"{config.db_prefix}{TEST_DB}", collection=ALLOPS, criteria={}),
        call(db_name=f"{config.db_prefix}{TEST_DB}", collection=WRITEONLY, criteria={}),
    ]
