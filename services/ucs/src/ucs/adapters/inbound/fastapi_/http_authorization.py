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

"""Authorization specific code for FastAPI"""

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ghga_service_commons.auth.jwt_auth import JWTAuthContextProvider
from ghga_service_commons.auth.policies import require_auth_context_using_credentials

from ucs.adapters.inbound.fastapi_ import dummies
from ucs.adapters.inbound.fastapi_ import rest_models as models
from ucs.config import Config

__all__ = [
    "JWTAuthContextProviderBundle",
    "require_change_file_box_work_order",
    "require_create_file_box_work_order",
    "require_create_file_work_order",
    "require_upload_file_work_order",
    "require_view_file_box_work_order",
]

CreateFileBoxProvider = JWTAuthContextProvider[models.CreateFileBoxWorkOrder]
ChangeFileBoxProvider = JWTAuthContextProvider[models.ChangeFileBoxWorkOrder]
ViewFileBoxProvider = JWTAuthContextProvider[models.ViewFileBoxWorkOrder]
CreateFileProvider = JWTAuthContextProvider[models.CreateFileWorkOrder]
UploadFileProvider = JWTAuthContextProvider[models.UploadFileWorkOrder]


class JWTAuthContextProviderBundle:
    """Bundle class that contains the different auth context providers"""

    def __init__(
        self,
        *,
        config: Config,
    ):
        """Bundled auth providers configurable at runtime"""
        self.uos_auth_config = config.uos_auth_config
        self.wps_auth_config = config.wps_auth_config

        self.create_file_box_provider = JWTAuthContextProvider(
            config=self.uos_auth_config,
            context_class=models.CreateFileBoxWorkOrder,
        )
        self.change_file_box_provider = JWTAuthContextProvider(
            config=self.uos_auth_config,
            context_class=models.ChangeFileBoxWorkOrder,
        )
        self.view_file_box_provider = JWTAuthContextProvider(
            config=self.uos_auth_config,
            context_class=models.ViewFileBoxWorkOrder,
        )
        self.create_file_provider = JWTAuthContextProvider(
            config=self.wps_auth_config,
            context_class=models.CreateFileWorkOrder,
        )
        self.upload_file_provider = JWTAuthContextProvider(
            config=self.wps_auth_config,
            context_class=models.UploadFileWorkOrder,
        )
        self.close_file_provider = JWTAuthContextProvider(
            config=self.wps_auth_config,
            context_class=models.CloseFileWorkOrder,
        )
        self.delete_file_provider = JWTAuthContextProvider(
            config=self.wps_auth_config,
            context_class=models.DeleteFileWorkOrder,
        )


async def _require_create_file_box_work_order(
    auth_provider_bundle: Annotated[
        JWTAuthContextProviderBundle,
        Depends(dummies.auth_provider_bundle),
    ],
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> models.CreateFileBoxWorkOrder:
    """Require a "create file box" work order context using FastAPI."""
    provider = auth_provider_bundle.create_file_box_provider
    return await require_auth_context_using_credentials(
        credentials=credentials, auth_provider=provider
    )


async def _require_change_file_box_work_order(
    auth_provider_bundle: Annotated[
        JWTAuthContextProviderBundle,
        Depends(dummies.auth_provider_bundle),
    ],
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> models.ChangeFileBoxWorkOrder:
    """Require a "change file box" work order context using FastAPI."""
    provider = auth_provider_bundle.change_file_box_provider
    return await require_auth_context_using_credentials(
        credentials=credentials, auth_provider=provider
    )


async def _require_view_file_box_work_order(
    auth_provider_bundle: Annotated[
        JWTAuthContextProviderBundle, Depends(dummies.auth_provider_bundle)
    ],
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> models.ViewFileBoxWorkOrder:
    """Require a "view file box" work order context using FastAPI."""
    provider = auth_provider_bundle.view_file_box_provider
    return await require_auth_context_using_credentials(
        credentials=credentials, auth_provider=provider
    )


async def _require_create_file_work_order(
    auth_provider_bundle: Annotated[
        JWTAuthContextProviderBundle, Depends(dummies.auth_provider_bundle)
    ],
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> models.CreateFileWorkOrder:
    """Require a "create file" work order context using FastAPI."""
    provider = auth_provider_bundle.create_file_provider
    return await require_auth_context_using_credentials(
        credentials=credentials, auth_provider=provider
    )


async def _require_upload_file_work_order(
    auth_provider_bundle: Annotated[
        JWTAuthContextProviderBundle, Depends(dummies.auth_provider_bundle)
    ],
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> models.UploadFileWorkOrder:
    """Require an "upload file" work order context using FastAPI."""
    provider = auth_provider_bundle.upload_file_provider
    return await require_auth_context_using_credentials(
        credentials=credentials, auth_provider=provider
    )


async def _require_close_file_work_order(
    auth_provider_bundle: Annotated[
        JWTAuthContextProviderBundle, Depends(dummies.auth_provider_bundle)
    ],
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> models.CloseFileWorkOrder:
    """Require a "close file" work order context using FastAPI."""
    provider = auth_provider_bundle.close_file_provider
    return await require_auth_context_using_credentials(
        credentials=credentials, auth_provider=provider
    )


async def _require_delete_file_work_order(
    auth_provider_bundle: Annotated[
        JWTAuthContextProviderBundle, Depends(dummies.auth_provider_bundle)
    ],
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
) -> models.DeleteFileWorkOrder:
    """Require a "delete file" work order context using FastAPI."""
    provider = auth_provider_bundle.delete_file_provider
    return await require_auth_context_using_credentials(
        credentials=credentials, auth_provider=provider
    )


require_create_file_box_work_order = Security(_require_create_file_box_work_order)
require_change_file_box_work_order = Security(_require_change_file_box_work_order)
require_view_file_box_work_order = Security(_require_view_file_box_work_order)
require_create_file_work_order = Security(_require_create_file_work_order)
require_upload_file_work_order = Security(_require_upload_file_work_order)
require_close_file_work_order = Security(_require_close_file_work_order)
require_delete_file_work_order = Security(_require_delete_file_work_order)
