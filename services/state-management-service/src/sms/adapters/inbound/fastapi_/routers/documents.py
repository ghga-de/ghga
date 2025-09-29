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

"""FastAPI routes for MongoDB state management."""

from json import JSONDecodeError
from typing import Annotated, Any

from fastapi import APIRouter, Path, Request, status
from fastapi.datastructures import QueryParams
from fastapi.exceptions import HTTPException

from sms.adapters.inbound.fastapi_ import dummies
from sms.adapters.inbound.fastapi_.http_authorization import (
    TokenAuthContext,
    require_token,
)
from sms.models import DocumentType, UpsertionDetails
from sms.ports.inbound.docs_handler import DocsHandlerPort

mongodb_router = APIRouter()

NAMESPACE_PARAM = Path(
    pattern=r"^(?P<db>[^.\\/\s\"$]{1,64})\.(?P<collection>[^$]{1,255})$",
    examples=["my_test_db.users"],
    description="The database and collection to query. Format: db_name.collection",
)

query_params_desc = (
    "Query parameters used to specify the documents affected by the request."
)
query_params_open_api: dict[str, Any] = {
    "parameters": [
        {
            "description": query_params_desc,
            "in": "query",
            "name": "criteria",
            "required": False,
            "schema": {
                "description": query_params_desc,
                "title": "Criteria",
                "type": "object",
                "additionalProperties": True,
                "examples": [
                    '{"name": "John"}',
                    '{"_id": {"$ne": "507f1f77bcf86cd799439011"}}',
                    '{"age": {"$gt": 21}}',
                ],
            },
        }
    ]
}


@mongodb_router.get(
    "/permissions",
    operation_id="get_db_permissions",
    summary="Returns the configured db permissions list.",
    status_code=200,
)
async def get_configured_permissions(
    config: dummies.ConfigDummy,
) -> list[str]:
    """Returns the configured db permissions list."""
    return config.db_permissions


def _check_for_multiple_query_params(query_params: QueryParams):
    """Inspect query parameters and raise an exception if any have multiple values."""
    # Sort both values and keys to ensure consistent error messages for tests
    multiples = [
        (k, sorted(query_params.getlist(k)))
        for k in query_params
        if len(query_params.getlist(k)) > 1
    ]
    multiples.sort(key=lambda tup: tup[0])

    if multiples:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Only one value per query parameter is allowed: {multiples}",
        )


@mongodb_router.get(
    "/{namespace}",
    operation_id="get_documents",
    summary="Returns all or some documents from the specified collection.",
    status_code=status.HTTP_200_OK,
    response_model=list[DocumentType],
    openapi_extra=query_params_open_api,
)
async def get_docs(
    namespace: Annotated[str, NAMESPACE_PARAM],
    docs_handler: dummies.DocsHandlerPortDummy,
    request: Request,
    _token: Annotated[TokenAuthContext, require_token],
) -> list[DocumentType]:
    """Returns all or some documents from the specified collection."""
    query_params = request.query_params

    _check_for_multiple_query_params(query_params)

    db_name, collection = namespace.split(".", 1)
    query_param_dict = dict(query_params)

    try:
        request_json = await request.json()
    except JSONDecodeError:
        request_json = {}

    if query_param_dict and request_json:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot supply search criteria through both request body and query params.",
        )

    criteria = request_json or query_param_dict

    try:
        results = await docs_handler.get(
            db_name=db_name,
            collection=collection,
            criteria=criteria,
        )
        return results
    except PermissionError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(err),
        ) from err
    except DocsHandlerPort.OperationError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err),
        ) from err
    except DocsHandlerPort.CriteriaFormatError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
    except DocsHandlerPort.NamespaceNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@mongodb_router.put(
    "/{namespace}",
    operation_id="upsert_documents",
    summary=(
        "Upserts the document(s) provided in the request body in the"
        + "specified collection."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
)
async def upsert_docs(
    namespace: Annotated[str, NAMESPACE_PARAM],
    upsertion_details: UpsertionDetails,
    docs_handler: dummies.DocsHandlerPortDummy,
    _token: Annotated[TokenAuthContext, require_token],
):
    """Upserts the document(s) provided in the request body in the specified collection."""
    db_name, collection = namespace.split(".", 1)
    try:
        await docs_handler.upsert(
            db_name=db_name,
            collection=collection,
            upsertion_details=upsertion_details,
        )
    except PermissionError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(err),
        ) from err
    except DocsHandlerPort.MissingIdFieldError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
    except DocsHandlerPort.OperationError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err),
        ) from err


@mongodb_router.delete(
    "/{namespace}",
    operation_id="delete_documents",
    summary="Deletes all or some documents in the collection.",
    description="No error is raised if the db or collection do not exist.",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=query_params_open_api,
)
async def delete_docs(
    namespace: Annotated[str, NAMESPACE_PARAM],
    request: Request,
    docs_handler: dummies.DocsHandlerPortDummy,
    _token: Annotated[TokenAuthContext, require_token],
):
    """Upserts the document(s) provided in the request body in the specified collection."""
    query_params: QueryParams = request.query_params

    _check_for_multiple_query_params(query_params)

    db_name, collection = namespace.split(".", 1)

    query_param_dict = dict(query_params)

    try:
        request_json = await request.json()
    except JSONDecodeError:
        request_json = {}

    if query_param_dict and request_json:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot supply search criteria through both request body and query params.",
        )

    criteria = request_json or query_param_dict

    try:
        await docs_handler.delete(
            db_name=db_name,
            collection=collection,
            criteria=criteria,
        )
    except PermissionError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(err),
        ) from err
    except DocsHandlerPort.OperationError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err),
        ) from err
    except (DocsHandlerPort.CriteriaFormatError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
