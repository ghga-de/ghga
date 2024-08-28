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

"""Test the objects-related REST API endpoints' behavior."""

import pytest
from hexkit.custom_types import JsonObject

from tests.fixtures.config import DEFAULT_TEST_CONFIG
from tests.fixtures.dummies import DummyObjectsHandler
from tests.fixtures.utils import VALID_BEARER_TOKEN, get_rest_client_with_mocks

pytestmark = pytest.mark.asyncio()

TEST_URL = "/objects"
INVALID_BUCKET_JSON = {"detail": "Bucket ID 'invalid' is invalid."}
INVALID_OBJECT_JSON = {"detail": "Object ID 'invalid' is invalid."}
BUCKET_NOT_FOUND_JSON = {
    "detail": "Bucket with ID 'non-existent-bucket' does not exist."
}

BASIC_STORAGE_MAP: dict[str, list[str]] = {"bucket": ["object1"]}
MULTI_OBJECT_MAP: dict[str, list[str]] = {"bucket": ["object1", "object2", "object3"]}
EMPTY_STORAGE_MAP: dict[str, list[str]] = {"empty-bucket": []}
DEFAULT_ALIAS = "primary"


@pytest.mark.parametrize(
    "bucket_id, object_id, expected_result, status_code",
    [
        ("bucket", "object1", True, 200),
        ("bucket", "non-existent-object", False, 200),
        ("non-existent-bucket", "object1", False, 200),
        ("invalid", "object1", INVALID_BUCKET_JSON, 422),
        ("bucket", "invalid", INVALID_OBJECT_JSON, 422),
    ],
    ids=[
        "HappyPath",
        "NonExistentObject",
        "NonExistentBucket",
        "InvalidBucket",
        "InvalidObject",
    ],
)
async def test_does_object_exist(
    bucket_id: str, object_id: str, expected_result: bool, status_code: int
):
    """Test the `does_object_exist` method.

    Check for:
    - Happy path (object exists)
    - Bucket exists, object does not
    - Bucket does not exist (error)
    - Invalid bucket ID (error)
    - Invalid object ID (error)
    """
    dummy_objects_handler = DummyObjectsHandler(
        storages={DEFAULT_ALIAS: BASIC_STORAGE_MAP}
    )
    async with get_rest_client_with_mocks(
        config=DEFAULT_TEST_CONFIG,
        objects_handler_override=dummy_objects_handler,
    ) as client:
        response = await client.get(
            f"{TEST_URL}/{DEFAULT_ALIAS}/{bucket_id}/{object_id}",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )

        assert response.json() == expected_result
        assert response.status_code == status_code


@pytest.mark.parametrize(
    "bucket_id, expected_result, status_code",
    [
        ("bucket", ["object1"], 200),
        ("empty-bucket", [], 200),
        ("non-existent-bucket", BUCKET_NOT_FOUND_JSON, 404),
        ("invalid", INVALID_BUCKET_JSON, 422),
    ],
    ids=["HappyPath", "EmptyBucket", "NonExistentBucket", "InvalidBucket"],
)
async def test_list_objects(
    bucket_id: str, expected_result: JsonObject, status_code: int
):
    """Test the /objects/{bucket_id} endpoint (list_objects).

    Check for:
    - Happy path (bucket exists, has objects)
    - Bucket exists, no objects
    - Bucket does not exist (error)
    - Invalid bucket ID (error)
    """
    dummy_objects_handler = DummyObjectsHandler(
        storages={DEFAULT_ALIAS: {**BASIC_STORAGE_MAP, **EMPTY_STORAGE_MAP}}
    )
    async with get_rest_client_with_mocks(
        config=DEFAULT_TEST_CONFIG,
        objects_handler_override=dummy_objects_handler,
    ) as client:
        response = await client.get(
            f"{TEST_URL}/{DEFAULT_ALIAS}/{bucket_id}",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )

        assert response.status_code == status_code
        assert response.json() == expected_result


@pytest.mark.parametrize(
    "bucket_id, status_code",
    [
        ("bucket", 204),
        ("empty-bucket", 204),
        ("non-existent-bucket", 204),
        ("invalid", 422),
    ],
)
async def test_delete_objects(bucket_id: str, status_code: int):
    """Test the /objects/{bucket_id} endpoint (empty bucket endpoint).

    Check for:
    - Happy path (bucket exists, has objects)
    - Bucket exists, no objects
    - Bucket does not exist (should not raise an error)
    - Invalid bucket ID (error)
    """
    # establish dummy with multiple objects
    dummy_objects_handler = DummyObjectsHandler(
        storages={DEFAULT_ALIAS: {**MULTI_OBJECT_MAP, **EMPTY_STORAGE_MAP}}
    )
    async with get_rest_client_with_mocks(
        config=DEFAULT_TEST_CONFIG,
        objects_handler_override=dummy_objects_handler,
    ) as client:
        response = await client.delete(
            f"{TEST_URL}/{DEFAULT_ALIAS}/{bucket_id}",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )

        assert response.status_code == status_code
        match status_code:
            case 204:
                assert not dummy_objects_handler.storages.get(bucket_id, [])
            case 422:
                assert response.json() == INVALID_BUCKET_JSON


async def test_auth():
    """Test that all /objects endpoints require authentication."""
    dummy_objects_handler = DummyObjectsHandler(
        storages={DEFAULT_ALIAS: BASIC_STORAGE_MAP}
    )
    async with get_rest_client_with_mocks(
        config=DEFAULT_TEST_CONFIG,
        objects_handler_override=dummy_objects_handler,
    ) as client:
        response = await client.get(
            f"{TEST_URL}/{DEFAULT_ALIAS}/bucket/object", headers={}
        )

        unauthenticated_json = {"detail": "Not authenticated"}
        assert response.status_code == 401
        assert response.json() == unauthenticated_json

        response = await client.get(f"{TEST_URL}/{DEFAULT_ALIAS}/bucket", headers={})
        assert response.status_code == 401
        assert response.json() == unauthenticated_json

        response = await client.delete(f"{TEST_URL}/{DEFAULT_ALIAS}/bucket", headers={})
        assert response.status_code == 401
        assert response.json() == unauthenticated_json


async def test_operation_errors():
    """Verify that operation errors generate a 500 response."""
    dummy_objects_handler = DummyObjectsHandler(
        storages={DEFAULT_ALIAS: BASIC_STORAGE_MAP}, raise_operation_error=True
    )
    async with get_rest_client_with_mocks(
        config=DEFAULT_TEST_CONFIG,
        objects_handler_override=dummy_objects_handler,
    ) as client:
        response = await client.get(
            f"{TEST_URL}/{DEFAULT_ALIAS}/bucket/object",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        operation_error_json = {
            "detail": "An error occurred while performing the object-storage operation."
        }
        assert response.status_code == 500
        assert response.json() == operation_error_json

        response = await client.get(
            f"{TEST_URL}/{DEFAULT_ALIAS}/bucket",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 500
        assert response.json() == operation_error_json

        response = await client.delete(
            f"{TEST_URL}/{DEFAULT_ALIAS}/bucket",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 500
        assert response.json() == operation_error_json


async def test_alias_not_configured():
    """Test that the right error is raised in each method when the alias is not configured."""
    dummy_objects_handler = DummyObjectsHandler(
        storages={DEFAULT_ALIAS: BASIC_STORAGE_MAP}
    )
    async with get_rest_client_with_mocks(
        config=DEFAULT_TEST_CONFIG,
        objects_handler_override=dummy_objects_handler,
    ) as client:
        response = await client.get(
            f"{TEST_URL}/non-existent-alias/bucket/object",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        alias_not_configured_json = {
            "detail": "The object storage alias 'non-existent-alias' is not configured."
        }
        assert response.status_code == 404
        assert response.json() == alias_not_configured_json

        response = await client.get(
            f"{TEST_URL}/non-existent-alias/bucket",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 404
        assert response.json() == alias_not_configured_json

        response = await client.delete(
            f"{TEST_URL}/non-existent-alias/bucket",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 404
        assert response.json() == alias_not_configured_json
