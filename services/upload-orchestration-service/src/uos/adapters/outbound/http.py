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

"""Outbound HTTP calls"""

import logging
from typing import Any
from uuid import UUID

import httpx
from ghga_event_schemas.pydantic_ import FileUpload
from ghga_service_commons.utils.utc_dates import UTCDatetime
from jwcrypto import jwk
from pydantic import UUID4, Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings

from uos.core.models import (
    BaseWorkOrderToken,
    ChangeFileBoxWorkOrder,
    CreateFileBoxWorkOrder,
    UploadGrant,
    ViewFileBoxWorkOrder,
)
from uos.core.tokens import sign_work_order_token
from uos.ports.outbound.http import AccessClientPort, FileBoxClientPort

TIMEOUT = 60

log = logging.getLogger(__name__)


class AccessApiConfig(BaseSettings):
    """Config parameters for managing upload access grants."""

    access_url: HttpUrl = Field(
        ...,
        description="URL pointing to the internal access API.",
        examples=["http://127.0.0.1/access"],
    )


class FileBoxClientConfig(BaseSettings):
    """Config parameters for interacting with the service owning FileUploadBoxes."""

    ucs_url: HttpUrl = Field(
        ...,
        description="URL pointing to the API of the service that owns FileUploadBoxes"
        + " (currently the UCS).",
        examples=["http://127.0.0.1/upload"],
    )
    work_order_signing_key: SecretStr = Field(
        ...,
        description="The private key for signing work order tokens",
        examples=['{"crv": "P-256", "kty": "EC", "x": "...", "y": "..."}'],
    )


class AccessClient(AccessClientPort):
    """An adapter for interacting with the access API to manage upload access grants"""

    def __init__(self, *, config: AccessApiConfig):
        self._access_url = config.access_url

    async def grant_upload_access(
        self,
        *,
        user_id: UUID4,
        iva_id: UUID4,
        box_id: UUID4,
        valid_from: UTCDatetime,
        valid_until: UTCDatetime,
    ) -> None:
        """Grant upload access to a user for a box.

        Raises:
            AccessAPIError: if there's a problem during the operation.
        """
        url = (
            f"{self._access_url}/upload-access/users"
            + f"/{user_id}/ivas/{iva_id}/boxes/{box_id}"
        )
        body = {
            "valid_from": valid_from.isoformat(),
            "valid_until": valid_until.isoformat(),
        }

        response = httpx.post(url, json=body)
        if response.status_code != 200:
            log.error(
                "Failed to grant upload access for user %s to box %s.",
                user_id,
                box_id,
                extra={
                    "user_id": user_id,
                    "iva_id": iva_id,
                    "box_id": box_id,
                    "valid_from": valid_from,
                    "valid_until": valid_until,
                    "status_code": response.status_code,
                    "response_text": response.text,
                },
            )
            raise self.AccessAPIError("Failed to grant upload access.")

    async def revoke_upload_access(self, *, grant_id: UUID4) -> None:
        """Revoke a user's access to an upload box.

        Raises:
            GrantNotFoundError: if the grant wasn't found.
            AccessAPIError: if there's a problem during the operation.
        """
        url = f"{self._access_url}/upload-access/grants/{grant_id}"
        response = httpx.delete(url)
        if response.status_code == 204:
            return

        if response.status_code == 404:
            raise self.GrantNotFoundError()
        elif response.status_code != 204:
            log.error(
                "Failed to revoke upload access for grant ID %s.",
                grant_id,
                extra={
                    "grant_id": grant_id,
                    "status_code": response.status_code,
                    "response_text": response.text,
                },
            )
            raise self.AccessAPIError("Failed to revoke upload access.")

    async def get_upload_access_grants(
        self,
        *,
        user_id: UUID4 | None = None,
        iva_id: UUID4 | None = None,
        box_id: UUID4 | None = None,
        valid: bool | None = None,
    ) -> list[UploadGrant]:
        """Get a list of upload grants.

        Raises:
            AccessAPIError: if there's a problem during the operation.
        """
        params: dict[str, Any] = {
            "user_id": str(user_id) if user_id is not None else user_id,
            "iva_id": str(iva_id) if iva_id is not None else iva_id,
            "box_id": str(box_id) if box_id is not None else box_id,
            "valid": valid,
        }

        url = f"{self._access_url}/upload-access/grants"
        response = httpx.get(url, params=params)
        if response.status_code != 200:
            msg = "Failed to retrieve upload access grants."
            log.error(
                msg,
                extra={
                    **params,
                    "status_code": response.status_code,
                    "response_text": response.text,
                },
            )
            raise self.AccessAPIError(msg)

        try:
            grants = [UploadGrant.model_validate(**grant) for grant in response.json()]
            return grants
        except Exception as err:
            msg = "Failed to extract grant information from response."
            log.error(msg, exc_info=True, extra=params)
            raise self.AccessAPIError(msg) from err

    async def get_accessible_upload_boxes(self, user_id: UUID4) -> list[UUID4]:
        """Get list of upload box IDs accessible to a user.

        Raises:
            AccessAPIError: if there's a problem during the operation.
        """
        url = f"{self._access_url}/upload-access/users/{user_id}/boxes"
        response = httpx.get(url)
        status_code = response.status_code
        if status_code == httpx.codes.NOT_FOUND:
            return []
        elif status_code != httpx.codes.OK:
            log.error(
                "Failed to retrieve list of research data upload boxes accessible to"
                + " user %s from the access API.",
                user_id,
                extra={"status_code": response.status_code},
            )
            raise self.AccessAPIError(
                f"Failed to retrieve list of boxes for user {user_id}"
            )

        try:
            box_ids = response.json()
            return [UUID(box_id) for box_id in box_ids]
        except Exception as err:
            msg = "Failed to extract box IDs from response."
            log.error(msg, exc_info=True, extra={"user_id": user_id})
            raise self.AccessAPIError(msg) from err

    async def check_box_access(self, *, user_id: UUID4, box_id: UUID4) -> bool:
        """Check if a user has access to a specific upload box.

        Raises:
            AccessAPIError: if there's a problem during the operation.
        """
        url = f"{self._access_url}/upload-access/users/{user_id}/boxes/{box_id}"

        try:
            response = httpx.get(url)

            # 200 means user has access, 403/404 means no access
            if response.status_code == 200:
                return True
            if response.status_code in (403, 404):
                return False
            log.error(
                "Unexpected response when checking box access for user %s and box %s.",
                user_id,
                box_id,
                extra={
                    "user_id": user_id,
                    "box_id": box_id,
                    "status_code": response.status_code,
                    "response_body": response.text,
                },
            )
            raise self.AccessAPIError("Failed to check box access.")

        except httpx.RequestError as err:
            log.error(
                "Request failed when checking box access for user %s and box %s.",
                user_id,
                box_id,
                exc_info=True,
                extra={"user_id": user_id, "box_id": box_id},
            )
            raise self.AccessAPIError("Failed to check box access.") from err


class FileBoxClient(FileBoxClientPort):
    """An adapter for interacting with the service that owns FileUploadBoxes.

    This class is responsible for WOT generation and all pertinent error handling.
    """

    def __init__(self, *, config: FileBoxClientConfig):
        self._ucs_url = config.ucs_url
        self._signing_key = jwk.JWK.from_json(
            config.work_order_signing_key.get_secret_value()
        )
        if not self._signing_key.has_private:
            key_error = KeyError("No private work order signing key found.")
            log.error(key_error)
            raise key_error

    def _auth_header(self, wot: BaseWorkOrderToken) -> dict[str, str]:
        signed_wot = sign_work_order_token(wot, self._signing_key)
        headers = {"Authorization": f"Bearer {signed_wot}"}
        return headers

    async def create_file_upload_box(self, *, storage_alias: str) -> UUID4:
        """Create a new FileUploadBox in owning service.

        Raises:
            OperationError if there's a problem with the operation.
        """
        headers = self._auth_header(CreateFileBoxWorkOrder())
        body = {"storage_alias": storage_alias}
        response = httpx.post(f"{self._ucs_url}/boxes", headers=headers, json=body)
        if response.status_code != 201:
            log.error(
                "Error creating new FileUploadBox in external service with storage alias %s.",
                storage_alias,
                extra={
                    "status_code": response.status_code,
                    "response_text": response.text,
                },
            )
            raise self.OperationError("Failed to create new FileUploadBox.")
        try:
            box_id = response.json()
            return UUID(box_id)
        except Exception as err:
            msg = "Failed to extract box ID from response body."
            log.error(msg, exc_info=True)
            raise self.OperationError(msg) from err

    async def lock_file_upload_box(self, *, box_id: UUID4) -> None:
        """Lock a FileUploadBox in the owning service.

        Raises:
            OperationError if there's a problem with the operation.
        """
        wot = ChangeFileBoxWorkOrder(work_type="lock", box_id=box_id)
        headers = self._auth_header(wot)
        body = {"lock": True}
        response = httpx.patch(
            f"{self._ucs_url}/boxes/{box_id}", headers=headers, json=body
        )
        if response.status_code != 204:
            log.error(
                "Error locking FileUploadBox ID %s in external service.",
                box_id,
                extra={
                    "status_code": response.status_code,
                    "response_text": response.text,
                },
            )
            raise self.OperationError("Failed to lock FileUploadBox.")

    async def unlock_file_upload_box(self, *, box_id: UUID4) -> None:
        """Unlock a FileUploadBox in the owning service.

        Raises:
            OperationError if there's a problem with the operation.
        """
        wot = ChangeFileBoxWorkOrder(work_type="unlock", box_id=box_id)

        headers = self._auth_header(wot)
        body = {"lock": False}
        response = httpx.patch(
            f"{self._ucs_url}/boxes/{box_id}", headers=headers, json=body
        )
        if response.status_code != 204:
            log.error(
                "Error unlocking FileUploadBox ID %s in external service.",
                box_id,
                extra={
                    "status_code": response.status_code,
                    "response_text": response.text,
                },
            )
            raise self.OperationError("Failed to unlock FileUploadBox.")

    async def get_file_upload_list(self, *, box_id: UUID4) -> list[FileUpload]:
        """Get list of file uploads in a FileUploadBox.

        Raises:
            OperationError if there's a problem with the operation.
        """
        wot = ViewFileBoxWorkOrder(box_id=box_id)
        headers = self._auth_header(wot)
        response = httpx.get(f"{self._ucs_url}/boxes/{box_id}/uploads", headers=headers)
        if response.status_code != 200:
            log.error(
                "Error unlocking FileUploadBox ID %s in external service.",
                box_id,
                extra={
                    "status_code": response.status_code,
                    "response_body": response.json(),
                },
            )
            raise self.OperationError("Failed to unlock FileUploadBox.")

        try:
            files = response.json()
            return [FileUpload(**file) for file in files]
        except Exception as err:
            msg = "Failed to extract list of file IDs from response body."
            log.error(msg, exc_info=True)
            raise self.OperationError(msg) from err
