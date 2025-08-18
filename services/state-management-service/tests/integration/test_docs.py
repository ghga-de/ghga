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

"""Integration tests for the database"""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.providers.mongodb.testutils import MongoDbFixture

from sms.inject import prepare_rest_app
from sms.models import DocumentType
from tests.fixtures.config import get_config
from tests.fixtures.utils import VALID_BEARER_TOKEN

pytestmark = pytest.mark.asyncio


ALLOPS = "testdb.allops"

IDS = [
    "8da92256-335e-4050-84c8-cf8ade02d488",
    "4fd199e1-78af-4c3e-9d7b-e38cea205bde",
    "95482e93-01ec-4f2c-9f5f-c2a9a8d8ac57",
    "24d9c9b5-f524-47f8-bbd0-50092bc5d35e",
]

DATES = [
    datetime(2025, 6, 1, 0, 0, 0, 451000, tzinfo=UTC),
    datetime(2025, 7, 1, 0, 0, 0, 451000, tzinfo=UTC),
    datetime(2025, 8, 1, 0, 0, 0, 451000, tzinfo=UTC),
    datetime(2025, 9, 1, 0, 0, 0, 451000, tzinfo=UTC),
]

SALLY: DocumentType = {
    "_id": IDS[0],
    "name": "sally",
    "age": 23,
    "created": DATES[0].isoformat(),
}
EZEKIEL: DocumentType = {
    "_id": IDS[1],
    "name": "ezekiel",
    "age": 53,
    "created": DATES[1].isoformat(),
}
DAVE: DocumentType = {
    "_id": IDS[2],
    "name": "dave",
    "age": 17,
    "created": DATES[2].isoformat(),
}
RAQUEL: DocumentType = {
    "_id": IDS[3],
    "name": "raquel",
    "age": 37,
    "created": DATES[3].isoformat(),
}

ALL_TEST_DOCS: list[DocumentType] = [SALLY, EZEKIEL, DAVE, RAQUEL]


@pytest.mark.parametrize(
    "query_params, body, expected_results",
    [
        ("", {}, ALL_TEST_DOCS),
        ("?name=sally", {}, [SALLY]),
        ('?age={"$gt":30}', {}, [EZEKIEL, RAQUEL]),
        ("", {"_id": {"$ne": {"$uuid": IDS[0]}}}, [EZEKIEL, DAVE, RAQUEL]),
    ],
    ids=["GetAllDocs", "NameIsSally", "AgeOver30", "AllIdsExceptFirstOne"],
)
async def test_get_docs(
    mongodb: MongoDbFixture,
    query_params: str,
    body: dict[str, Any],
    expected_results: list[DocumentType],
):
    """Test problem-free reading documents from the database."""
    config = get_config(sources=[mongodb.config])

    # Use extended json to specify type info for UUIDs and dates
    docs_to_insert = deepcopy(ALL_TEST_DOCS)
    for i in range(len(docs_to_insert)):
        doc = cast(dict, docs_to_insert[i])
        doc["_id"] = {"$uuid": doc["_id"]}
        doc["created"] = {"$date": doc["created"]}
        docs_to_insert[i] = doc

    async with (
        prepare_rest_app(config=config, events_handler_override=AsyncMock()) as app,
        AsyncTestClient(app=app) as client,
    ):
        await client.put(
            f"/documents/{ALLOPS}",
            headers={"Authorization": VALID_BEARER_TOKEN},
            json={"documents": docs_to_insert},
        )

        response = await client.request(
            method="GET",
            url=f"/documents/{ALLOPS}{query_params}",
            headers={"Authorization": VALID_BEARER_TOKEN},
            json=body,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == len(expected_results)
        data.sort(key=lambda x: x["_id"])
        for i, doc in enumerate(data):
            data[i]["created"] = doc["created"].replace("Z", "+00:00")
        expected_results.sort(key=lambda x: x["_id"])
        assert data == expected_results


@pytest.mark.parametrize(
    "criteria, error_text",
    [
        (
            "?age={unquoted_key:53}",
            "The value for query parameter 'age' is invalid.",
        ),
        (
            "?age=34&age=33",
            "Only one value per query parameter is allowed: [('age', ['33', '34'])]",
        ),
    ],
)
@pytest.mark.parametrize("http_method", ["get", "delete"])
async def test_invalid_criteria(http_method: str, criteria: str, error_text: str):
    """Test the handling of invalid criteria."""
    config = get_config()
    async with (
        prepare_rest_app(config=config, events_handler_override=AsyncMock()) as app,
        AsyncTestClient(app=app) as client,
    ):
        method_to_call = getattr(client, http_method)
        response = await method_to_call(
            f"/documents/{ALLOPS}{criteria}",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 422
        assert response.json() == {"detail": error_text}


@pytest.mark.parametrize("http_method", ["get", "put", "delete"])
async def test_get_docs_permission_error(http_method: str):
    """Test the handling of a PermissionError."""
    config = get_config()
    op_name = "read" if http_method == "get" else "write"
    rule = f"unlisted.unlisted:{op_name[0]}"

    message = (
        f"'{op_name.title()}' operations not allowed on db 'unlisted',"
        + f" collection 'unlisted'. No rule found that matches '{rule}'"
    )
    async with (
        prepare_rest_app(config=config, events_handler_override=AsyncMock()) as app,
        AsyncTestClient(app=app) as client,
    ):
        method_to_call = getattr(client, http_method)
        put_args: dict[str, Any] = (
            {"json": {"documents": {}}} if http_method == "put" else {}
        )
        response = await method_to_call(
            "/documents/unlisted.unlisted",
            headers={"Authorization": VALID_BEARER_TOKEN},
            **put_args,
        )
        assert response.status_code == 403
        assert response.json() == {"detail": message}


async def test_deletion_on_nonexistent_resources(mongodb: MongoDbFixture):
    """Test delete method on nonexistent dbs, collections.

    There should not be any error raised.
    """
    base_config = get_config(sources=[mongodb.config])
    db_permissions = ["*.*:*"]
    new_config = base_config.model_copy(update={"db_permissions": db_permissions})
    config = get_config(sources=[new_config])

    async with (
        prepare_rest_app(config=config, events_handler_override=AsyncMock()) as app,
        AsyncTestClient(app=app) as client,
    ):
        # Delete nonexistent db contents with fully specified namespace
        response = await client.delete(
            "/documents/nonexistent.nonexistent",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 204

        # Delete nonexistent db contents with wildcard collection
        response = await client.delete(
            "/documents/nonexistent.*",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 204

        # Delete nonexistent collection contents
        response = await client.delete(
            "/documents/testdb.doesnotexist",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 204
