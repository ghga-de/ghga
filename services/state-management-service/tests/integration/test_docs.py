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

"""Integration tests for the database"""

from typing import Any

import pytest
from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.providers.mongodb.testutils import MongoDbFixture

from sms.inject import prepare_rest_app
from sms.models import DocumentType
from tests.fixtures.config import get_config

pytestmark = pytest.mark.asyncio

VALID_BEARER_TOKEN = "Bearer 43fadc91-b98f-4925-bd31-1b054b13dc55"
ALLOPS = "testdb.allops"

SALLY: DocumentType = {"_id": 1, "name": "sally", "age": 23}
EZEKIEL: DocumentType = {"_id": 2, "name": "ezekiel", "age": 53}
DAVE: DocumentType = {"_id": 3, "name": "dave", "age": 17}
RAQUEL: DocumentType = {"_id": 4, "name": "raquel", "age": 37}

ALL_TEST_DOCS: list[DocumentType] = [
    SALLY,
    EZEKIEL,
    DAVE,
    RAQUEL,
]


@pytest.mark.parametrize(
    "query_params, expected_results",
    [
        ("", ALL_TEST_DOCS),
        ("?name=sally", [SALLY]),
        ('?age={"$gt":30}', [EZEKIEL, RAQUEL]),
        ('?_id={"$ne":1}', [EZEKIEL, DAVE, RAQUEL]),
    ],
    ids=["all", "name_is_sally", "age_over_30", "ids_over_1"],
)
async def test_get_docs(
    mongodb: MongoDbFixture,
    query_params: str,
    expected_results: list[DocumentType],
):
    """Test problem-free reading documents from the database."""
    config = get_config(sources=[mongodb.config])

    async with (
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
    ):
        await client.put(
            f"/documents/{ALLOPS}",
            headers={"Authorization": VALID_BEARER_TOKEN},
            json={"documents": ALL_TEST_DOCS},
        )

        response = await client.get(
            f"/documents/{ALLOPS}{query_params}",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        data.sort(key=lambda x: x["_id"])
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
        prepare_rest_app(config=config) as app,
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
        prepare_rest_app(config=config) as app,
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
        prepare_rest_app(config=config) as app,
        AsyncTestClient(app=app) as client,
    ):
        # Insert documents into testdb.allops
        await client.put(
            f"/documents/{ALLOPS}",
            headers={"Authorization": VALID_BEARER_TOKEN},
            json={"documents": ALL_TEST_DOCS},
        )

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
