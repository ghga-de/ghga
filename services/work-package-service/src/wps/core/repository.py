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
#

"""A repository for work packages."""

import logging
from datetime import timedelta
from uuid import UUID

from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.crypt import encrypt
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.utils import now_utc_ms_prec
from jwcrypto import jwk
from pydantic import UUID4, Field, SecretStr
from pydantic_settings import BaseSettings

from wps.core.models import (
    BoxWithExpiration,
    CloseFileWorkOrder,
    CreateFileWorkOrder,
    Dataset,
    DatasetWithExpiration,
    DeleteFileWorkOrder,
    DownloadWorkOrder,
    ResearchDataUploadBoxBasics,
    UploadFileWorkOrder,
    UploadPathType,
    ViewFileBoxWorkOrder,
    WorkPackage,
    WorkPackageCreationData,
    WorkPackageCreationResponse,
    WorkPackageType,
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
    UploadBoxDaoPort,
    WorkPackageDaoPort,
)

log = logging.getLogger(__name__)


class WorkPackageConfig(BaseSettings):
    """Config parameters needed for the WorkPackageRepository."""

    datasets_collection: str = Field(
        "datasets",
        description="The name of the database collection for datasets",
    )
    upload_boxes_collection: str = Field(
        "uploadBoxes",
        description="The name of the database collection for upload boxes",
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


FileUploadToken = UploadFileWorkOrder | CloseFileWorkOrder | DeleteFileWorkOrder
WORK_TYPE_TO_MODEL: dict[str, type[FileUploadToken]] = {
    "upload": UploadFileWorkOrder,
    "close": CloseFileWorkOrder,
    "delete": DeleteFileWorkOrder,
}


class WorkPackageRepository(WorkPackageRepositoryPort):
    """A repository for work packages."""

    def __init__(
        self,
        *,
        config: WorkPackageConfig,
        access_check: AccessCheckPort,
        dataset_dao: DatasetDaoPort,
        upload_box_dao: UploadBoxDaoPort,
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
        self._upload_box_dao = upload_box_dao
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
        try:
            user_id = UUID(auth_context.id)
        except ValueError as error:
            access_error = self.WorkPackageAccessError("Malformed user ID supplied")
            log.error(access_error)
            raise access_error from error

        if user_id is None:
            access_error = self.WorkPackageAccessError("No internal user specified")
            log.error(access_error)
            raise access_error

        dataset_id = creation_data.dataset_id
        box_id = creation_data.box_id

        match creation_data.type:
            case WorkPackageType.DOWNLOAD:
                return await self._create_download_work_package(
                    creation_data,
                    auth_context,
                    user_id,
                    dataset_id,  # type: ignore
                )
            case WorkPackageType.UPLOAD:
                return await self._create_upload_work_package(
                    creation_data,
                    auth_context,
                    user_id,
                    box_id,  # type: ignore
                )

    async def _create_download_work_package(
        self,
        creation_data: WorkPackageCreationData,
        auth_context: AuthContext,
        user_id: UUID,
        dataset_id: str,
    ) -> WorkPackageCreationResponse:
        """Create a download work package."""
        extra = {  # only used for logging
            "user_id": user_id,
            "dataset_id": dataset_id,
            "work_package_type": WorkPackageType.DOWNLOAD,
        }

        expires = await self._access.check_download_access(user_id, dataset_id)
        if not expires:
            access_error = self.WorkPackageAccessError(
                "Missing dataset access permission"
            )
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

        return await self._create_work_package_record(
            creation_data, auth_context, user_id, expires, files, dataset_id=dataset_id
        )

    async def _create_upload_work_package(
        self,
        creation_data: WorkPackageCreationData,
        auth_context: AuthContext,
        user_id: UUID,
        box_id: UUID,
    ) -> WorkPackageCreationResponse:
        """Create an upload work package."""
        extra = {  # only used for logging
            "user_id": user_id,
            "box_id": box_id,
            "work_package_type": WorkPackageType.UPLOAD,
        }

        expires = await self._access.check_upload_access(user_id, box_id)
        if not expires:
            access_error = self.WorkPackageAccessError(
                "Missing upload box access permission"
            )
            log.error(access_error, extra=extra)
            raise access_error

        # For upload work packages, files aren't used, so the arg is an empty dict
        return await self._create_work_package_record(
            creation_data, auth_context, user_id, expires, {}, box_id=box_id
        )

    async def _create_work_package_record(  # noqa: PLR0913
        self,
        creation_data: WorkPackageCreationData,
        auth_context: AuthContext,
        user_id: UUID,
        expires: UTCDatetime,
        files: dict[str, str],
        *,
        dataset_id: str | None = None,
        box_id: UUID4 | None = None,
    ) -> WorkPackageCreationResponse:
        """Create the work package database record."""
        full_user_name = auth_context.name
        if auth_context.title:
            full_user_name = auth_context.title + " " + full_user_name

        created = now_utc_ms_prec()
        expires = min(created + self._valid_timedelta, expires)

        token = generate_work_package_access_token()
        user_public_crypt4gh_key = creation_data.user_public_crypt4gh_key

        work_package = WorkPackage(
            dataset_id=dataset_id,
            box_id=box_id,
            type=creation_data.type,
            files=files,
            user_id=user_id,
            full_user_name=full_user_name,
            email=auth_context.email,
            user_public_crypt4gh_key=creation_data.user_public_crypt4gh_key,
            token_hash=hash_token(token),
            created=created,
            expires=expires,
        )
        await self._dao.insert(work_package)
        encrypted_token = encrypt(token, user_public_crypt4gh_key)

        return WorkPackageCreationResponse(
            id=str(work_package.id), token=encrypted_token, expires=expires
        )

    async def get(
        self,
        work_package_id: UUID,
        *,
        check_valid: bool = True,
        work_package_access_token: str | None = None,
    ) -> WorkPackage:
        """Get a work package with the given ID from the repository.

        In the following cases, a WorkPackageAccessError is raised:
        - if a work package with the given work_package_id does not exist
        - if the file_id is not contained in the work package
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
            extra = {"work_package_id": work_package.id}  # only used for logging
            if not work_package.created <= now_utc_ms_prec() < work_package.expires:
                access_error = self.WorkPackageAccessError("Work package has expired")
                log.error(access_error, extra=extra)
                raise access_error
            # Check access based on work package type
            if work_package.type == WorkPackageType.DOWNLOAD:
                has_access = await self._access.check_download_access(
                    work_package.user_id,
                    work_package.dataset_id,  # type: ignore
                )
            elif work_package.type == WorkPackageType.UPLOAD:
                has_access = await self._access.check_upload_access(
                    work_package.user_id,
                    work_package.box_id,  # type: ignore
                )
            else:  # pragma: no cover
                has_access = False

            if not has_access:
                access_error = self.WorkPackageAccessError(
                    f"{work_package.type.value.title()} access has been revoked"
                )
                log.error(access_error, extra=extra)
                raise access_error
        return work_package

    async def get_download_wot(
        self,
        *,
        work_package_id: UUID4,
        file_id: str,
        check_valid: bool = True,
        work_package_access_token: str | None = None,
    ) -> str:
        """Create a download work order token for a given work package and file.

        In the following cases, a WorkPackageAccessError is raised:
        - if a work package with the given work_package_id does not exist
        - if the file_id is not contained in the work package
        - if check_valid is set and the work package has expired
        - if the work package type is not DOWNLOAD
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

        extra["work_package_type"] = work_package.type

        if work_package.type != WorkPackageType.DOWNLOAD:
            access_error = self.WorkPackageAccessError(
                "Work package type must be DOWNLOAD to obtain a download access WOT"
            )
            log.error(access_error, extra=extra)
            raise access_error

        # For Download-type work packages, the file ID must be in the list of files
        if file_id not in (work_package.files or {}):
            access_error = self.WorkPackageAccessError(
                "File is not contained in work package"
            )
            log.error(access_error, extra=extra)
            raise access_error

        wot = DownloadWorkOrder(
            file_id=file_id,
            user_public_crypt4gh_key=work_package.user_public_crypt4gh_key,
        )
        signed_wot = sign_work_order_token(wot, self._signing_key)
        return encrypt(signed_wot, work_package.user_public_crypt4gh_key)

    async def get_upload_wot(  # noqa: PLR0913
        self,
        *,
        work_package_id: UUID4,
        work_type: UploadPathType,
        box_id: UUID4,
        alias: str | None = None,
        file_id: UUID4 | None = None,
        check_valid: bool = True,
        work_package_access_token: str | None = None,
    ) -> str:
        """Create an upload work order token for a given work package, work type,
        box id, file id and alias.

        The box ID populated in upload WOTs is the file_upload_box ID, not the main
        ResearchDataUploadBox ID.

        In the following cases, a WorkPackageAccessError is raised:
        - if a work package with the given work_package_id does not exist
        - if the work type is not valid, i.e. one of create, upload, close, or delete
        - if the work_type requires parameters that are not provided (alias or file ID)
        - if check_valid is set and the work package has expired
        - if a work_package_access_token is specified and it does not match
          the token hash that is stored in the work package
        - if an upload box is not found in the database
        """
        extra = {  # only used for logging
            "work_package_id": work_package_id,
            "file_id": file_id,
            "alias": alias,
            "work_order_type": work_type,
            "check_valid": check_valid,
        }

        work_package = await self.get(
            work_package_id,
            check_valid=check_valid,
            work_package_access_token=work_package_access_token,
        )

        extra["work_package_type"] = work_package.type

        # Retrieve the ResearchDataUploadBox in order to get its FileUploadBox ID
        try:
            research_data_upload_box = await self._upload_box_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            access_error = self.WorkPackageAccessError("Upload box does not exist")
            log.error(access_error, extra=extra)
            raise access_error from err
        file_upload_box_id = research_data_upload_box.file_upload_box_id

        user_public_crypt4gh_key = work_package.user_public_crypt4gh_key
        match work_type:
            case "create":
                work_order = CreateFileWorkOrder(
                    alias=alias,  # type: ignore
                    box_id=file_upload_box_id,
                    user_public_crypt4gh_key=user_public_crypt4gh_key,
                )
            case "upload" | "close" | "delete":
                work_order = WORK_TYPE_TO_MODEL[work_type](
                    box_id=file_upload_box_id,
                    file_id=file_id,  # type: ignore
                    user_public_crypt4gh_key=user_public_crypt4gh_key,
                )
            case "view":
                work_order = ViewFileBoxWorkOrder(  # type: ignore[assignment]
                    box_id=file_upload_box_id,
                    user_public_crypt4gh_key=user_public_crypt4gh_key,
                )
            case _:  # pragma: no cover
                access_error = self.WorkPackageAccessError(
                    f"Unsupported Work Order Token type: {work_type}"
                )
                log.error(access_error, extra=extra)
                raise access_error
        signed_wot = sign_work_order_token(work_order, self._signing_key)
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
        self, *, auth_context: AuthContext
    ) -> list[DatasetWithExpiration]:
        """Get the list of all datasets accessible to the authenticated user.

        The returned datasets also have an expiration date until when access is granted.
        """
        try:
            user_id = UUID(auth_context.id)
        except ValueError as error:
            access_error = self.WorkPackageAccessError("Malformed user ID supplied")
            log.error(access_error)
            raise access_error from error

        if user_id is None:
            access_error = self.WorkPackageAccessError("No internal user specified")
            log.error(access_error)
            raise access_error

        dataset_id_to_expiration = (
            await self._access.get_accessible_datasets_with_expiration(user_id)
        )
        datasets_with_expiration: list[DatasetWithExpiration] = []
        for dataset_id in dataset_id_to_expiration:
            try:
                dataset = await self.get_dataset(dataset_id)
            except self.DatasetNotFoundError:
                log.debug("Dataset '%s' not found, continuing...", dataset_id)
                continue
            dataset_with_expiration = DatasetWithExpiration(
                **dataset.model_dump(), expires=dataset_id_to_expiration[dataset_id]
            )
            datasets_with_expiration.append(dataset_with_expiration)
        return datasets_with_expiration

    async def register_upload_box(
        self, upload_box: ResearchDataUploadBoxBasics
    ) -> None:
        """Register an upload box."""
        await self._upload_box_dao.upsert(upload_box)
        log.info("Upserted UploadBox with ID %s", upload_box.id)

    async def delete_upload_box(self, box_id: UUID4) -> None:
        """Delete an upload box with the given ID."""
        try:
            await self._upload_box_dao.delete(id_=box_id)
            log.info("Deleted UploadBox with ID %s", box_id)
        except ResourceNotFoundError:
            log.info(
                "UploadBox with ID %s not found, presumed already deleted.", box_id
            )

    async def get_upload_box(self, box_id: UUID4) -> ResearchDataUploadBoxBasics:
        """Get a registered upload box using the given ID.

        Raises an `UploadBoxNotFoundError` if no doc with the box_id exists.
        """
        try:
            return await self._upload_box_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            error = self.UploadBoxNotFoundError("UploadBox not found")
            log.error(error, extra={"box_id": box_id})
            raise error from err

    async def get_upload_boxes(self, *, user_id: UUID4) -> list[BoxWithExpiration]:
        """Get the list of all upload boxes accessible to the authenticated user
        along with access expiry.
        """
        # Get accessible upload boxes from access service
        box_id_to_expiration = await self._access.get_accessible_boxes_with_expiration(
            user_id
        )
        log.debug(
            "Retrieved %i upload boxes for user %s",
            len(box_id_to_expiration),
            user_id,
        )

        upload_boxes: list[BoxWithExpiration] = []
        for box_id, expiration in box_id_to_expiration.items():
            try:
                upload_box = await self.get_upload_box(box_id)
                box_with_expiration = BoxWithExpiration(
                    **upload_box.model_dump(), expires=expiration
                )
                upload_boxes.append(box_with_expiration)
            except self.UploadBoxNotFoundError:
                log.debug("Upload box '%s' not found, continuing...", box_id)
                continue

        return upload_boxes
