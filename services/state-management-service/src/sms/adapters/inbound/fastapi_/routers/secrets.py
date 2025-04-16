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

"""FastAPI routes for HashiCorp Vault state management."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from pydantic import Field

from sms.adapters.inbound.fastapi_ import dummies
from sms.adapters.inbound.fastapi_.http_authorization import (
    TokenAuthContext,
    require_token,
)

secrets_router = APIRouter()

vault_path_field = Field(
    default=..., description="The path to the vault", examples=["ekss", "sms"]
)


@secrets_router.get(
    "/{vault_path}",
    operation_id="get_secrets",
    summary="Returns a list of secrets in the vault",
    status_code=status.HTTP_200_OK,
    response_model=list[str],
)
async def get_secrets(
    secrets_handler: dummies.SecretsHandlerPortDummy,
    _token: Annotated[TokenAuthContext, require_token],
    vault_path: Annotated[str, vault_path_field],
):
    """Returns a list of secrets in the specified vault"""
    try:
        return secrets_handler.get_secrets(vault_path)
    except PermissionError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(err)
        ) from err
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@secrets_router.delete(
    "/{vault_path}",
    operation_id="delete_secrets",
    summary="""Delete all secrets from the specified vault.""",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_secrets(
    secrets_handler: dummies.SecretsHandlerPortDummy,
    _token: Annotated[TokenAuthContext, require_token],
    vault_path: Annotated[str, vault_path_field],
):
    """Delete all secrets from the specified vault."""
    try:
        secrets_handler.delete_secrets(vault_path)
    except PermissionError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(err)
        ) from err
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
