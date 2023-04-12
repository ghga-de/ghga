# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
#

"""A repository for work packages."""

from datetime import timedelta
from typing import Optional

from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.utc_dates import now_as_utc
from jwcrypto import jwk
from pydantic import BaseSettings, Field, SecretStr

from wps.core.crypt import encrypt
from wps.core.models import (
    WorkOrderToken,
    WorkPackage,
    WorkPackageCreationData,
    WorkPackageCreationResponse,
    WorkPackageData,
)
from wps.core.tokens import (
    generate_work_package_access_token,
    hash_token,
    sign_work_order_token,
)
from wps.ports.inbound.repository import WorkPackageRepositoryPort
from wps.ports.outbound.dao import ResourceNotFoundError, WorkPackageDaoPort


class WorkPackageConfig(BaseSettings):
    """Config parameters needed for the WorkPackageRepository."""

    work_packages_collection: str = Field(
        "workPacakges",
        description="The name of the database collection for work packages",
    )
    work_package_valid_days: int = Field(
        30,
        description="How many days a work package (and its access token) stays valid",
    )
    work_package_signing_key: SecretStr = Field(
        ...,
        description="The private key for signing work order tokens",
        example='{"crv": "P-256", "kty": "EC", "x": "...", "y": "..."}',
    )


class WorkPackageRepository(WorkPackageRepositoryPort):
    """A repository for work packages."""

    def __init__(
        self,
        *,
        config: WorkPackageConfig,
        work_package_dao: WorkPackageDaoPort,
    ):
        """Initialize with specific configuration and outbound adapter."""
        self._valid_timedelta = timedelta(config.work_package_valid_days)
        self._signing_key = jwk.JWK.from_json(
            config.work_package_signing_key.get_secret_value()
        )
        if not self._signing_key.has_private:
            raise KeyError("No private work order signing key found.")
        self._dao = work_package_dao

    async def create(
        self, creation_data: WorkPackageCreationData, auth_context: AuthContext
    ) -> WorkPackageCreationResponse:
        """Create a work package and store it in the repository."""

        # Here we still need to check whether all file IDs are contained
        # in the dataset specified in creation_data,
        # and replaced with all file IDs if empty.
        # The file extensions need to be also determined here.
        file_ids = creation_data.file_ids
        file_extensions: dict[str, str] = {}

        full_user_name = auth_context.name
        if auth_context.title:
            full_user_name = auth_context.title + " " + full_user_name

        created = now_as_utc()
        expires = created + self._valid_timedelta

        token = generate_work_package_access_token()
        user_public_crypt4gh_key = creation_data.user_public_crypt4gh_key

        work_package_data = WorkPackageData(
            dataset_id=creation_data.dataset_id,
            type=creation_data.type,
            file_ids=file_ids,
            file_extensions=file_extensions,
            user_id=auth_context.id,
            full_user_name=full_user_name,
            email=auth_context.email,
            user_public_crypt4gh_key=creation_data.user_public_crypt4gh_key,
            token_hash=hash_token(token),
            created=created,
            expires=expires,
        )
        work_package = await self._dao.insert(work_package_data)
        encrypted_token = encrypt(token, user_public_crypt4gh_key)
        return WorkPackageCreationResponse(id=work_package.id, token=encrypted_token)

    async def get(
        self,
        work_package_id: str,
        check_valid: bool = True,
        work_package_access_token: Optional[str] = None,
    ) -> WorkPackage:
        """Get a work package with the given ID from the repository.

        In the following cases, a WorkPackageAccessError is raised:
        - if a work package with the given work_package_id does not exist
        - if check_valid is set and the work package has expired
        - if a work_package_access_token is specified and it does not match
          the token hash that is stored in the work package
        """
        try:
            work_package = await self._dao.get_by_id(work_package_id)
        except ResourceNotFoundError as error:
            raise self.WorkPackageAccessError from error
        if (
            check_valid
            and not work_package.created <= now_as_utc() <= work_package.expires
        ):
            raise self.WorkPackageAccessError
        if work_package_access_token and work_package.token_hash != hash_token(
            work_package_access_token
        ):
            raise self.WorkPackageAccessError
        return work_package

    async def work_order_token(
        self,
        work_package_id: str,
        file_id: str,
        check_valid: bool = True,
        work_package_access_token: Optional[str] = None,
    ) -> str:
        """Create a work order token for a given work package and file.

        In the following cases, a WorkPackageAccessError is raised:
        - if the work package does not exist
        - if the file_id is not contained in the work package
        - if check_valid is set and the work package has expired
        - if a work_package_access_token is specified and it does not match
          the token hash that is stored in the work package
        """
        work_package = await self.get(
            work_package_id,
            check_valid=check_valid,
            work_package_access_token=work_package_access_token,
        )
        if file_id not in work_package.file_ids:
            raise self.WorkPackageAccessError
        public_key = work_package.user_public_crypt4gh_key
        wot = WorkOrderToken(
            type=work_package.type,
            file_id=file_id,
            user_id=work_package.user_id,
            public_key=public_key,
            full_user_name=work_package.full_user_name,
            email=work_package.email,
        )
        signed_wot = sign_work_order_token(wot, self._signing_key)
        return encrypt(signed_wot, public_key)
