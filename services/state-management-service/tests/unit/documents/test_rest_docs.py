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

"""Test the REST API endpoints for /documents/"""

from collections.abc import Mapping
from typing import Any
from unittest.mock import AsyncMock

import pytest

from sms.core.docs_handler import DocsHandler
from sms.models import DocumentType, UpsertionDetails
from sms.ports.inbound.docs_handler import DocsHandlerPort
from sms.ports.outbound.docs_dao import DocsDaoPort
from tests.fixtures.config import DEFAULT_TEST_CONFIG
from tests.fixtures.dummies import DocsApiCallArgs, DummyDocsHandler
from tests.fixtures.utils import VALID_BEARER_TOKEN, get_rest_client_with_mocks

pytestmark = pytest.mark.asyncio()

TEST_URL = "/documents/testdb.testcollection"
PERMISSION_ERROR_URL = "/documents/testdb.permission_error"


async def test_health_check():
    """Test the health check endpoint."""
    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=DummyDocsHandler()
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}


async def test_permissions_retrieval():
    """Test the permissions retrieval endpoint."""
    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=DummyDocsHandler()
    ) as client:
        response = await client.get("/documents/permissions")
        assert response.status_code == 200
        assert response.json() == DEFAULT_TEST_CONFIG.db_permissions


@pytest.mark.parametrize(
    "namespace",
    ["...", "..x", ".x.y", "te$t.x", "te st.x", "te/st.x", 'te"st.x', "te\\st.x"],
)
async def test_incorrect_namespace(namespace: str):
    """Test for error when supplying a namespace with the wrong format"""
    bad_namespace_url = f"/documents/{namespace}"
    error_code = 404 if "/" in namespace else 422
    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=DummyDocsHandler()
    ) as client:
        response = await client.get(
            bad_namespace_url,
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == error_code

        response = await client.put(
            bad_namespace_url,
            headers={"Authorization": VALID_BEARER_TOKEN},
            json={"documents": []},
        )
        assert response.status_code == error_code

        response = await client.delete(
            bad_namespace_url,
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == error_code


@pytest.mark.parametrize(
    "headers",
    [{"Authorization": "Bearer 123"}, {}],
    ids=["WrongApiKey", "NoApiKey"],
)
@pytest.mark.parametrize(
    "http_method",
    ["get", "put", "delete"],
    ids=["GET", "PUT", "DELETE"],
)
async def test_unauthenticated_calls(http_method: str, headers: dict[str, str]):
    """Test unauthenticated calls, which should result in a 401 Unauthorized code."""
    dummy_docs_handler = DummyDocsHandler()
    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=dummy_docs_handler
    ) as client:
        method_to_call = getattr(client, http_method)
        response = await method_to_call(TEST_URL, headers=headers)

    # Verify status code and make sure there were no DAO method calls
    assert response.status_code == 401
    assert dummy_docs_handler.calls == []


@pytest.mark.parametrize(
    "http_method, expected_status_code",
    [
        ("get", 200),
        ("put", 204),
        ("delete", 204),
    ],
    ids=["GET", "PUT", "DELETE"],
)
async def test_authenticated_valid_calls(http_method: str, expected_status_code: int):
    """Verify authenticated calls are successfully passed to the handler."""
    # Create dummy docs handler populated with the db/collection we'll query to avoid errors
    dummy_docs_handler = DummyDocsHandler(state={"testdb": {"testcollection": {}}})
    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=dummy_docs_handler
    ) as client:
        method_to_call = getattr(client, http_method)

        put_args: dict[str, Any] = (
            {"json": {"documents": {}}} if http_method == "put" else {}
        )
        response = await method_to_call(
            url=TEST_URL,
            headers={"Authorization": VALID_BEARER_TOKEN},
            **put_args,
        )

    # Verify status code and DAO method calls
    assert response.status_code == expected_status_code, response.json()
    call = DocsApiCallArgs(
        method=http_method,
        db_name="testdb",
        collection="testcollection",
        criteria=None if http_method == "put" else {},
        upsertion_details=None
        if http_method != "put"
        else UpsertionDetails(documents={}),
    )
    assert dummy_docs_handler.calls == [call]


@pytest.mark.parametrize(
    "http_method, expected_status_code",
    [("get", 200), ("delete", 204)],
    ids=["GET", "DELETE"],
)
@pytest.mark.parametrize(
    "query_string, as_dict",
    [
        # Test with a few different query strings
        ("name=Alice&age=34", {"name": "Alice", "age": "34"}),
        ("name=Alice&age=34&", {"name": "Alice", "age": "34"}),
        (
            "name=Ellen_Ripley&age=62&location=",
            {"name": "Ellen_Ripley", "age": "62", "location": ""},
        ),
    ],
)
async def test_calls_with_query_params(
    http_method: str,
    expected_status_code: int,
    query_string: str,
    as_dict: Mapping[str, str],
):
    """Verify calls with query parameters (GET and DELETE)."""
    # Create dummy docs handler populated with the db/collection we'll query to avoid errors
    dummy_docs_handler = DummyDocsHandler(state={"testdb": {"testcollection": {}}})
    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=dummy_docs_handler
    ) as client:
        method_to_call = getattr(client, http_method)
        response = await method_to_call(
            url=f"{TEST_URL}?{query_string}",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )

    # Verify status code and DAO method calls
    assert response.status_code == expected_status_code
    call = DocsApiCallArgs(
        method=http_method,
        db_name="testdb",
        collection="testcollection",
        criteria=as_dict,
    )
    assert dummy_docs_handler.calls == [call]


@pytest.mark.parametrize(
    "http_method",
    ["get", "put", "delete"],
    ids=["GET", "PUT", "DELETE"],
)
async def test_permission_errors(
    http_method: str,
):
    """Test that permission errors are handled correctly."""
    dummy_docs_handler = DummyDocsHandler()
    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=dummy_docs_handler
    ) as client:
        method_to_call = getattr(client, http_method)
        put_args: dict[str, Any] = (
            {"json": {"documents": {}}} if http_method == "put" else {}
        )
        response = await method_to_call(
            url=PERMISSION_ERROR_URL,
            headers={"Authorization": VALID_BEARER_TOKEN},
            **put_args,
        )
    assert response.status_code == 403

    assert len(dummy_docs_handler.calls) == 1
    assert dummy_docs_handler.calls[0].method == http_method


async def test_put_with_docs():
    """Test PUT with documents."""
    dummy_docs_handler = DummyDocsHandler()
    docs_to_insert: list[DocumentType] = [{"name": "Alice"}, {"name": "Bob"}]
    upsertion_details = UpsertionDetails(documents=docs_to_insert)
    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=dummy_docs_handler
    ) as client:
        response = await client.put(
            url=TEST_URL,
            headers={"Authorization": VALID_BEARER_TOKEN},
            json=upsertion_details.model_dump(),
        )

    # Verify status code and DAO method calls
    assert response.status_code == 204
    call = DocsApiCallArgs(
        method="put",
        db_name="testdb",
        collection="testcollection",
        upsertion_details=UpsertionDetails(documents=docs_to_insert),
    )
    assert dummy_docs_handler.calls == [call]


async def test_put_with_missing_id_field():
    """Test that a missing id field in the documents causes a 422 error."""
    config = DEFAULT_TEST_CONFIG
    docs_dao = AsyncMock(spec=DocsDaoPort)
    docs_handler = DocsHandler(config=config, docs_dao=docs_dao)
    # Try to insert docs without specifying an id field (default is _id)
    docs_to_insert: list[DocumentType] = [
        {"_id": "1", "name": "Alice"},
        {"name": "Bob"},
    ]
    upsertion_details = UpsertionDetails(documents=docs_to_insert)
    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=docs_handler
    ) as client:
        response = await client.put(
            url="/documents/testdb.allops",
            headers={"Authorization": VALID_BEARER_TOKEN},
            json=upsertion_details.model_dump(),
        )

    # Verify status code and DAO method calls
    assert response.status_code == 422


async def test_failed_db_operation():
    """Test that a failed DB operation results in a 500 error."""
    dummy_docs_handler = AsyncMock(spec=DocsHandlerPort)
    dummy_docs_handler.get.side_effect = DocsHandlerPort.OperationError()
    dummy_docs_handler.upsert.side_effect = DocsHandlerPort.OperationError()
    dummy_docs_handler.delete.side_effect = DocsHandlerPort.OperationError()

    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=dummy_docs_handler
    ) as client:
        response = await client.get(
            url=PERMISSION_ERROR_URL,
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 500

        response = await client.put(
            url=PERMISSION_ERROR_URL,
            headers={"Authorization": VALID_BEARER_TOKEN},
            json=UpsertionDetails(documents={}).model_dump(),
        )
        assert response.status_code == 500

        response = await client.delete(
            url=PERMISSION_ERROR_URL,
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 500


@pytest.mark.parametrize("http_method", ["get", "delete"])
async def test_criteria_format_error_handling(http_method: str):
    """Test that CriteriaFormatError is handled correctly."""
    dummy_docs_handler = AsyncMock(spec=DocsHandlerPort)
    expected_error = DocsHandlerPort.CriteriaFormatError(key="test")
    dummy_docs_handler.get.side_effect = expected_error
    dummy_docs_handler.delete.side_effect = expected_error

    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=dummy_docs_handler
    ) as client:
        method_to_call = getattr(client, http_method)
        response = await method_to_call(
            url=TEST_URL,
            headers={"Authorization": VALID_BEARER_TOKEN},
        )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "namespace, expected_status_code",
    [
        ("test.*", 204),
        ("*.testcoll.ection", 422),
        ("*.*", 204),
    ],
    ids=["AllCollectionsInOneDb", "Invalid", "AllCollectionsInAllDbs"],
)
async def test_wildcard_deletion(namespace: str, expected_status_code: int):
    """Test that a wildcard deletion is handled correctly."""
    dummy_docs_handler = DummyDocsHandler()
    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=dummy_docs_handler
    ) as client:
        response = await client.delete(
            url=f"/documents/{namespace}",
            headers={"Authorization": VALID_BEARER_TOKEN},
        )

    assert response.status_code == expected_status_code
    db_name, collection = namespace.split(".", 1)
    assert dummy_docs_handler.calls == [
        DocsApiCallArgs(
            method="delete", db_name=db_name, collection=collection, criteria={}
        )
    ]


async def test_missing_db():
    """Test that a missing DB results in a 404 error."""
    dummy_docs_handler = DummyDocsHandler(state={"somedb": {"testcollection": {}}})
    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=dummy_docs_handler
    ) as client:
        response = await client.get(
            url=TEST_URL,
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 404


async def test_missing_collection():
    """Test that a missing collection results in a 404 error."""
    dummy_docs_handler = DummyDocsHandler(state={"testdb": {"somecollection": {}}})
    async with get_rest_client_with_mocks(
        DEFAULT_TEST_CONFIG, docs_handler_override=dummy_docs_handler
    ) as client:
        response = await client.get(
            url=TEST_URL,
            headers={"Authorization": VALID_BEARER_TOKEN},
        )
        assert response.status_code == 404
