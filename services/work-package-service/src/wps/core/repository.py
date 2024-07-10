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
#

"""A repository for work packages."""

import logging
from datetime import timedelta

from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.crypt import encrypt
from ghga_service_commons.utils.utc_dates import now_as_utc
from jwcrypto import jwk
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from wps.core.models import (
    Dataset,
    WorkOrderToken,
    WorkPackage,
    WorkPackageCreationData,
    WorkPackageCreationResponse,
    WorkPackageData,
    WorkType,
)
from wps.core.tokens import (
    generate_work_package_access_token,
    hash_token,
    sign_work_order_token,
)
from wps.ports.inbound.repository import WorkPackageRepositoryPort
from wps.ports.outbound.access import AccessCheckPort
from wps.ports.outbound.dao import (
    DatasetDaoPort,
    ResourceNotFoundError,
    WorkPackageDaoPort,
)

log = logging.getLogger(__name__)


class WorkPackageConfig(BaseSettings):
    """Config parameters needed for the WorkPackageRepository."""

    datasets_collection: str = Field(
        "datasets",
        description="The name of the database collection for datasets",
    )
    work_packages_collection: str = Field(
        "workPackages",
        description="The name of the database collection for work packages",
    )
    work_package_valid_days: int = Field(
        30,
        description="How many days a work package (and its access token) stays valid",
    )
    work_package_signing_key: SecretStr = Field(
        ...,
        description="The private key for signing work order tokens",
        examples=['{"crv": "P-256", "kty": "EC", "x": "...", "y": "..."}'],
    )


class WorkPackageRepository(WorkPackageRepositoryPort):
    """A repository for work packages."""

    def __init__(
        self,
        *,
        config: WorkPackageConfig,
        access_check: AccessCheckPort,
        dataset_dao: DatasetDaoPort,
        work_package_dao: WorkPackageDaoPort,
    ):
        """Initialize with specific configuration and outbound adapter."""
        self._valid_timedelta = timedelta(config.work_package_valid_days)
        self._signing_key = jwk.JWK.from_json(
            config.work_package_signing_key.get_secret_value()
        )
        if not self._signing_key.has_private:
            key_error = KeyError("No private work order signing key found.")
            log.error(key_error)
            raise key_error
        self._access = access_check
        self._dataset_dao = dataset_dao
        self._dao = work_package_dao

    async def create(
        self, *, creation_data: WorkPackageCreationData, auth_context: AuthContext
    ) -> WorkPackageCreationResponse:
        """Create a work package and store it in the repository.

        In the following cases, a WorkPackageAccessError is raised:
        - no internal user specified via auth_context
        - no access permission to the specified dataset
        - the specified work type is not supported
        - the files in th dataset cannot be determined
        - no existing files in the dataset have been specified
        """
        user_id = auth_context.id
        if user_id is None:
            access_error = self.WorkPackageAccessError("No internal user specified")
            log.error(access_error)
            raise access_error

        dataset_id = creation_data.dataset_id
        work_type = creation_data.type

        extra = {  # only used for logging
            "user_id": user_id,
            "dataset_id": dataset_id,
            "work_type": work_type,
        }

        if work_type == WorkType.DOWNLOAD:
            if not await self._access.check_download_access(user_id, dataset_id):
                access_error = self.WorkPackageAccessError(
                    "Missing dataset access permission"
                )
                log.error(access_error, extra=extra)
                raise access_error
        else:
            access_error = self.WorkPackageAccessError("Unsupported work type")
            log.error(access_error, extra=extra)
            raise access_error

        try:
            dataset = await self.get_dataset(dataset_id)
        except self.DatasetNotFoundError as error:
            access_error = self.WorkPackageAccessError("Cannot determine dataset files")
            log.error(access_error, extra=extra)
            raise access_error from error

        file_ids = [file.id for file in dataset.files]
        if creation_data.file_ids is not None:
            # if file_ids is not passed as None, restrict the file set
            file_id_set = set(creation_data.file_ids)
            file_ids = [file_id for file_id in file_ids if file_id in file_id_set]
        if not file_ids:
            access_error = self.WorkPackageAccessError(
                "No existing files have been specified"
            )
            log.error(access_error, extra=extra)
            raise access_error

        file_id_set = set(file_ids)
        files = {
            file.id: file.extension for file in dataset.files if file.id in file_id_set
        }

        full_user_name = auth_context.name
        if auth_context.title:
            full_user_name = auth_context.title + " " + full_user_name

        created = now_as_utc()
        expires = created + self._valid_timedelta

        token = generate_work_package_access_token()
        user_public_crypt4gh_key = creation_data.user_public_crypt4gh_key

        work_package_data = WorkPackageData(
            dataset_id=dataset_id,
            type=work_type,
            files=files,
            user_id=user_id,
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
        *,
        check_valid: bool = True,
        work_package_access_token: str | None = None,
    ) -> WorkPackage:
        """Get a work package with the given ID from the repository.

        In the following cases, a WorkPackageAccessError is raised:
        - if a work package with the given work_package_id does not exist
        - if check_valid is set and the work package has expired
        - if a work_package_access_token is specified and it does not match
          the token hash that is stored in the work package
        """
        extra = {"work_package_id": work_package_id}  # only used for logging

        try:
            work_package = await self._dao.get_by_id(work_package_id)
        except ResourceNotFoundError as error:
            access_error = self.WorkPackageAccessError("Work package not found")
            log.error(access_error, extra=extra)
            raise access_error from error

        if work_package_access_token and work_package.token_hash != hash_token(
            work_package_access_token
        ):
            access_error = self.WorkPackageAccessError(
                "Invalid work package access token"
            )
            log.error(access_error, extra=extra)
            raise access_error

        if check_valid:
            if not work_package.created <= now_as_utc() <= work_package.expires:
                access_error = self.WorkPackageAccessError("Work package has expired")
                log.error(access_error, extra=extra)
                raise access_error

            if work_package.type == WorkType.DOWNLOAD:
                if not await self._access.check_download_access(
                    work_package.user_id, work_package.dataset_id
                ):
                    access_error = self.WorkPackageAccessError(
                        "Access has been revoked"
                    )
                    log.error(access_error, extra=extra)
                    raise access_error
            else:
                access_error = self.WorkPackageAccessError("Unsupported work type")
                log.error(access_error, extra=extra)
                raise access_error

        return work_package

    async def work_order_token(
        self,
        *,
        work_package_id: str,
        file_id: str,
        check_valid: bool = True,
        work_package_access_token: str | None = None,
    ) -> str:
        """Create a work order token for a given work package and file.

        In the following cases, a WorkPackageAccessError is raised:
        - if the work package does not exist
        - if the file_id is not contained in the work package
        - if check_valid is set and the work package has expired
        - if a work_package_access_token is specified and it does not match
          the token hash that is stored in the work package
        """
        extra = {  # only used for logging
            "work_package_id": work_package_id,
            "file_id": file_id,
            "check_valid": check_valid,
        }

        work_package = await self.get(
            work_package_id,
            check_valid=check_valid,
            work_package_access_token=work_package_access_token,
        )

        if file_id not in work_package.files:
            access_error = self.WorkPackageAccessError(
                "File is not contained in work package"
            )
            log.error(access_error, extra=extra)
            raise access_error

        user_public_crypt4gh_key = work_package.user_public_crypt4gh_key
        wot = WorkOrderToken(
            type=work_package.type,
            file_id=file_id,
            user_id=work_package.user_id,
            user_public_crypt4gh_key=user_public_crypt4gh_key,
            full_user_name=work_package.full_user_name,
            email=work_package.email,
        )
        signed_wot = sign_work_order_token(wot, self._signing_key)
        return encrypt(signed_wot, user_public_crypt4gh_key)

    async def register_dataset(self, dataset: Dataset) -> None:
        """Register a dataset with all of its files."""
        await self._dataset_dao.upsert(dataset)

    async def delete_dataset(self, dataset_id: str) -> None:
        """Delete a dataset with all of its files.

        If the dataset does not exist, a DatasetNotFoundError will be raised.
        """
        try:
            await self._dataset_dao.delete(id_=dataset_id)
        except ResourceNotFoundError as error:
            dataset_not_found_error = self.DatasetNotFoundError("Dataset not found")
            log.error(dataset_not_found_error, extra={"dataset_id": dataset_id})
            raise dataset_not_found_error from error

    async def get_dataset(self, dataset_id: str) -> Dataset:
        """Get a registered dataset using the given ID.

        If the dataset does not exist, a DatasetNotFoundError will be raised.
        """
        try:
            return await self._dataset_dao.get_by_id(dataset_id)
        except ResourceNotFoundError as error:
            dataset_not_found_error = self.DatasetNotFoundError("Dataset not found")
            log.error(dataset_not_found_error, extra={"dataset_id": dataset_id})
            raise dataset_not_found_error from error

    async def get_datasets(
        self, *, auth_context: AuthContext, work_type: WorkType | None = None
    ) -> list[Dataset]:
        """Get the list of all datasets accessible to the authenticated user.

        A work type can be specified for filtering the datasets. If no work type is
        specified, the datasets for all work types (upload and download) are returned.

        Note that currently only downloadable datasets are supported.
        """
        user_id = auth_context.id
        if user_id is None:
            access_error = self.WorkPackageAccessError("No internal user specified")
            log.error(access_error)
            raise access_error

        if work_type is not None and work_type != WorkType.DOWNLOAD:
            access_error = self.WorkPackageAccessError("Unsupported work type")
            log.error(access_error, extra={"work_type": work_type})
            raise access_error

        dataset_ids = await self._access.get_datasets_with_download_access(user_id)
        datasets: list[Dataset] = []
        for dataset_id in dataset_ids:
            try:
                dataset = await self.get_dataset(dataset_id)
            except self.DatasetNotFoundError:
                log.debug("Dataset '%s' not found, continuing...", dataset_id)
                continue
            datasets.append(dataset)
        return datasets
