# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from typing import Any, Literal
from uuid import UUID

import httpx
from ghga_service_commons.utils.utc_dates import UTCDatetime
from jwcrypto import jwk
from pydantic import UUID4, Field, HttpUrl, PositiveInt, SecretStr
from pydantic_settings import BaseSettings

from rs.constants import HTTPX_TIMEOUT, UCS_UPLOADS_PAGE_SIZE
from rs.core.models import (
    BaseWorkOrderToken,
    ChangeFileBoxWorkOrder,
    CreateFileBoxWorkOrder,
    DeleteFileBoxWorkOrder,
    DeleteFileUploadWorkOrder,
    FileUploadWithAccession,
    GrantId,
    ResizeFileBoxWorkOrder,
    UploadGrant,
    ViewFileBoxWorkOrder,
)
from rs.core.tokens import sign_work_order_token
from rs.ports.outbound.http import (
    AccessClientPort,
    FileBoxClientPort,
)

log = logging.getLogger(__name__)


def _extract_exception_id(response: httpx.Response) -> str | None:
    """Safely pull the ``exception_id`` out of a (possibly malformed) error response.

    Returns ``None`` when the body isn't valid JSON, isn't a JSON object, or has no
    ``exception_id`` field, so callers can branch on the value without first checking
    the shape of the response body.
    """
    try:
        return response.json()["exception_id"]
    except (KeyError, ValueError, TypeError):
        return None


class WOTSigningConfig(BaseSettings):
    """Base config for JWT use"""

    work_order_signing_key: SecretStr = Field(
        default=...,
        description="The private key for signing work order tokens and other JWTs",
        examples=['{"crv": "P-256", "kty": "EC", "x": "...", "y": "..."}'],
    )


class AccessApiConfig(BaseSettings):
    """Config parameters for managing upload access grants."""

    access_url: HttpUrl = Field(
        default=...,
        description="URL pointing to the internal access API.",
        examples=["http://127.0.0.1/access"],
    )


class AccessClient(AccessClientPort):
    """An adapter for interacting with the access API to manage upload access grants"""

    def __init__(self, *, config: AccessApiConfig, httpx_client: httpx.AsyncClient):
        self._access_url = str(config.access_url).rstrip("/")
        self._client = httpx_client

    async def grant_upload_access(
        self,
        *,
        user_id: UUID4,
        iva_id: UUID4,
        box_id: UUID4,
        valid_from: UTCDatetime,
        valid_until: UTCDatetime,
    ) -> GrantId:
        """Grant upload access to a user for a box.

        Returns the created grant ID.

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

        response = await self._client.post(url, json=body, timeout=HTTPX_TIMEOUT)
        if response.status_code != 201:
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
        try:
            return GrantId(id=response.json()["id"])
        except Exception as err:
            msg = (
                "Failed to extract the ID of the newly created access grant"
                " from the response body."
            )
            log.error(msg, exc_info=True)
            raise self.AccessAPIError(msg) from err

    async def revoke_upload_access(self, *, grant_id: UUID4) -> None:
        """Revoke a user's access to an upload box.

        Raises:
            GrantNotFoundError: if the grant wasn't found.
            AccessAPIError: if there's a problem during the operation.
        """
        url = f"{self._access_url}/upload-access/grants/{grant_id}"
        response = await self._client.delete(url, timeout=HTTPX_TIMEOUT)
        if response.status_code == 204:
            return

        if response.status_code == 404:
            raise self.GrantNotFoundError()
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
        params = {key: value for key, value in params.items() if value is not None}

        url = f"{self._access_url}/upload-access/grants"
        response = await self._client.get(url, params=params, timeout=HTTPX_TIMEOUT)
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
            return [UploadGrant.model_validate(grant) for grant in response.json()]
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
        response = await self._client.get(url, timeout=HTTPX_TIMEOUT)
        status_code = response.status_code
        if status_code == httpx.codes.NOT_FOUND:
            return []
        if status_code != httpx.codes.OK:
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
            response = await self._client.get(url, timeout=HTTPX_TIMEOUT)

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


class FileBoxClientConfig(WOTSigningConfig):
    """Config parameters for interacting with the service owning
    FileUploadBoxes.
    """

    ucs_url: HttpUrl = Field(
        default=...,
        description="URL pointing to the API of the service that owns FileUploadBoxes"
        + " (currently the UCS).",
        examples=["http://127.0.0.1/upload"],
    )


class FileBoxClient(FileBoxClientPort):
    """An adapter for interacting with the service that owns FileUploadBoxes.

    This class is responsible for WOT generation and all pertinent error handling.
    """

    def __init__(self, *, config: FileBoxClientConfig, httpx_client: httpx.AsyncClient):
        self._ucs_url = str(config.ucs_url).rstrip("/")
        self._client = httpx_client
        self._signing_key = jwk.JWK.from_json(
            config.work_order_signing_key.get_secret_value()
        )
        if not self._signing_key.has_private:
            key_error = KeyError("No private work order signing key found.")
            log.error(key_error)
            raise key_error

    def _auth_header(self, wot: BaseWorkOrderToken) -> dict[str, str]:
        signed_wot = sign_work_order_token(wot, self._signing_key)
        return {"Authorization": f"Bearer {signed_wot}"}

    def _raise_for_409(
        self,
        *,
        response: httpx.Response,
        body: dict[str, Any],
        operation: Literal[
            "lock", "unlock", "archive", "resize", "delete file from", "delete"
        ],
        box_id: UUID4,
    ):
        """Log and raise an error for a 409 response."""
        exception_id = _extract_exception_id(response)
        extra = {"box_id": box_id, "response_text": response.text}
        for field in ["version", "max_size"]:
            if field in body:
                extra[field] = body[field]

        if exception_id == "incompleteUploads":
            # exception_id parsed, so the body is a JSON object we can re-read
            raw = response.json().get("data", {}).get("incomplete_uploads", [])
            incomplete_file_ids = [UUID(item[0]) for item in raw]
            extra["incomplete_uploads"] = incomplete_file_ids
            log.error(
                "Failed to %s FileUploadBox %s: %d file(s) have incomplete uploads.",
                operation,
                box_id,
                len(incomplete_file_ids),
                extra=extra,
            )
            raise self.FUBIncompleteUploadsError(
                incomplete_file_ids=incomplete_file_ids
            )
        if exception_id == "boxVersionOutdated":
            log.error(
                "Failed to %s FileUploadBox %s because the version specified"
                + " in the request is out of date.",
                operation,
                box_id,
                extra=extra,
            )
            raise self.FUBVersionError(box_id=box_id)
        if exception_id == "boxMaxSizeTooLow":
            max_size = body["max_size"]
            log.error(
                "Failed to resize FileUploadBox %s because the new max_size %i is"
                + " smaller than the bytes already uploaded.",
                box_id,
                max_size,
                extra=extra,
            )
            raise self.FUBMaxSizeTooLowError(
                f"New max_size {max_size} is smaller than the bytes already uploaded."
            )
        if exception_id == "boxStateError":
            msg = (
                f"Cannot {operation} FileUploadBox {box_id} because the box's state"
                + " prevents it. The RS and UCS box states might be out of sync."
            )
            log.error(msg, extra=extra)
            raise self.FUBStateError(msg)
        msg = (
            f"Failed to {operation} FileUploadBox {box_id} because the response status"
            + f" code was 409 but the exception ID ({exception_id}) was missing or"
            + " unrecognized."
        )
        log.error(msg, extra=body)
        raise self.OperationError(msg)

    async def create_file_upload_box(
        self, *, storage_alias: str, max_size: PositiveInt
    ) -> UUID4:
        """Create a new FileUploadBox in owning service.

        Raises:
            OperationError if there's a problem with the operation.
        """
        headers = self._auth_header(CreateFileBoxWorkOrder())
        body = {"storage_alias": storage_alias, "max_size": max_size}
        response = await self._client.post(
            f"{self._ucs_url}/boxes", headers=headers, json=body, timeout=HTTPX_TIMEOUT
        )
        if response.status_code != 201:
            log.error(
                "Error creating new FileUploadBox in external service with storage"
                " alias %s.",
                storage_alias,
                extra={
                    "status_code": response.status_code,
                    "response_text": response.text,
                },
            )
            if response.status_code == 400:
                # Make error text more specific if it's a storage alias problem
                raise self.OperationError(
                    f"{storage_alias} is not a valid storage alias."
                )
            raise self.OperationError("Failed to create new FileUploadBox.")

        try:
            box_id = response.json()
            return UUID(box_id)
        except Exception as err:
            msg = "Failed to extract box ID from response body."
            log.error(msg, exc_info=True)
            raise self.OperationError(msg) from err

    async def lock_file_upload_box(
        self, *, box_id: UUID4, version: int, force: bool = False
    ) -> None:
        """Lock a FileUploadBox in the owning service.

        Raises:
            FUBVersionError if the remote box version differs from `version`.
            OperationError if there's a problem with the operation.
        """
        wot = ChangeFileBoxWorkOrder(work_type="lock", box_id=box_id)
        headers = self._auth_header(wot)
        body = {"version": version, "state": "locked", "force": force}
        response = await self._client.patch(
            f"{self._ucs_url}/boxes/{box_id}",
            headers=headers,
            json=body,
            timeout=HTTPX_TIMEOUT,
        )
        if response.status_code == 409:
            self._raise_for_409(
                response=response, body=body, operation="lock", box_id=box_id
            )
        elif response.status_code != 204:
            log.error(
                "Error locking FileUploadBox ID %s in external service.",
                box_id,
                extra={
                    "status_code": response.status_code,
                    "response_text": response.text,
                },
            )
            raise self.OperationError("Failed to lock FileUploadBox.")

    async def unlock_file_upload_box(self, *, box_id: UUID4, version: int) -> None:
        """Unlock a FileUploadBox in the owning service.

        Raises:
            FUBVersionError if the remote box version differs from `version`.
            OperationError if there's a problem with the operation.
        """
        wot = ChangeFileBoxWorkOrder(work_type="unlock", box_id=box_id)

        headers = self._auth_header(wot)
        body = {"version": version, "state": "open"}
        response = await self._client.patch(
            f"{self._ucs_url}/boxes/{box_id}",
            headers=headers,
            json=body,
            timeout=HTTPX_TIMEOUT,
        )
        if response.status_code == 409:
            self._raise_for_409(
                response=response,
                body=body,
                operation="unlock",
                box_id=box_id,
            )
        elif response.status_code != 204:
            log.error(
                "Error unlocking FileUploadBox ID %s in external service.",
                box_id,
                extra={
                    "status_code": response.status_code,
                    "response_text": response.text,
                },
            )
            raise self.OperationError("Failed to unlock FileUploadBox.")

    async def get_file_upload_list(  # noqa: PLR0913
        self,
        *,
        box_id: UUID4,
        skip: int = 0,
        limit: int | None = None,
        sort: list[str] | None = None,
        with_checksums: bool = False,
        missing_box_ok: bool = False,
    ) -> tuple[list[FileUploadWithAccession], int]:
        """Get a page of file uploads in a FileUploadBox.

        Returns a 2-tuple of the page's file uploads and the total (unpaginated) count.
        It is assumed that `skip`, `limit`, and `sort` are validated beforehand - they
        are not validated in this method.

        `skip`, `limit`, and `sort` are forwarded to the owning service's paginated
        endpoint. `sort` is a list of FileUpload field names to sort by, each optionally
        prefixed with a dash to denote descending order. When omitted, the owning
        service's default ordering (by alias) is used.

        `with_checksums` is forwarded to the owning service to control whether the
        per-part checksum lists (`encrypted_parts_md5` and `encrypted_parts_sha256`) are
        included on each file upload. When False, the owning service returns None for
        those fields.

        If the FileUploadBox does not exist and `missing_box_ok` is set to True, this
        method will return an empty page. Otherwise it will raise an OperationError.

        Raises:
            OperationError if there's a problem with the operation.
        """
        wot = ViewFileBoxWorkOrder(box_id=box_id)
        headers = self._auth_header(wot)
        params: dict[str, Any] = {"skip": skip, "with_checksums": with_checksums}
        if limit is not None:
            params["limit"] = limit
        if sort:
            # Forward as a single comma-separated value (non-exploded) to match the
            # owning service's query-param convention. Passing the list directly would
            # make httpx emit repeated `sort=...` params instead.
            params["sort"] = ",".join(sort)
        response = await self._client.get(
            f"{self._ucs_url}/boxes/{box_id}/uploads",
            headers=headers,
            params=params,
            timeout=HTTPX_TIMEOUT,
        )
        if response.status_code != 200:
            if response.status_code == 404 and missing_box_ok:
                log.warning(
                    "Received a 404 when getting files list for FileUploadBox %s."
                    + " It is likely that conflicting state exists between RS and UCS."
                    + " Returning an empty page to continue processing.",
                    box_id,
                )
                return [], 0
            log.error(
                "Error getting file list for FileUploadBox %s.",
                box_id,
                extra={
                    "file_upload_box_id": box_id,
                    "status_code": response.status_code,
                    "response_body": response.json(),
                },
            )
            raise self.OperationError("Failed to get FileUploadBox file list.")

        try:
            page = response.json()
            file_uploads = [FileUploadWithAccession(**file) for file in page["items"]]
            total_count = page["total_count"]
        except Exception as err:
            msg = "Failed to extract list of file uploads from response body."
            log.error(msg, exc_info=True)
            raise self.OperationError(msg) from err

        return file_uploads, total_count

    async def get_all_file_uploads(
        self,
        *,
        box_id: UUID4,
        with_checksums: bool = False,
        missing_box_ok: bool = False,
    ) -> list[FileUploadWithAccession]:
        """Get every file upload in a FileUploadBox by paging through the endpoint.

        Use this instead of `get_file_upload_list` when the complete set of uploads is
        required (e.g. for deletion or validation) rather than a single page.

        `with_checksums` determines if per-part checksum lists are populated or `None`.

        If the FileUploadBox does not exist and `missing_box_ok` is set to True, this
        method will return an empty list. Otherwise it will raise an OperationError.

        Raises:
            OperationError if there's a problem with the operation.
        """
        file_uploads: list[FileUploadWithAccession] = []
        skip = 0
        while True:
            page, total_count = await self.get_file_upload_list(
                box_id=box_id,
                skip=skip,
                limit=UCS_UPLOADS_PAGE_SIZE,
                with_checksums=with_checksums,
                missing_box_ok=missing_box_ok,
            )
            file_uploads.extend(page)
            skip += len(page)

            # Stop once every upload is collected
            if skip >= total_count or not page:
                break

        return file_uploads

    async def archive_file_upload_box(self, *, box_id: UUID4, version: int) -> None:
        """Archive a FileUploadBox in the owning service.

        Raises:
            FUBVersionError if the remote box version differs from `version`.
            OperationError if there's any other problem with the operation.
        """
        wot = ChangeFileBoxWorkOrder(work_type="archive", box_id=box_id)
        headers = self._auth_header(wot)
        body = {"version": version, "state": "archived"}
        response = await self._client.patch(
            f"{self._ucs_url}/boxes/{box_id}",
            headers=headers,
            json=body,
            timeout=HTTPX_TIMEOUT,
        )
        if response.status_code == 409:
            self._raise_for_409(
                response=response,
                body=body,
                operation="archive",
                box_id=box_id,
            )
        elif response.status_code != 204:
            log.error(
                "Error archiving FileUploadBox ID %s in external service.",
                box_id,
                extra={
                    "status_code": response.status_code,
                    "response_text": response.text,
                },
            )
            raise self.OperationError("Failed to archive FileUploadBox.")

    async def resize_file_upload_box(
        self, *, box_id: UUID4, version: int, max_size: PositiveInt
    ) -> None:
        """Resize a FileUploadBox in the owning service.

        Raises:
            FUBVersionError if the remote box version differs from `version`.
            FUBMaxSizeTooLowError if the new max_size is smaller than bytes already
            uploaded.
            OperationError if there's a problem with the operation.
        """
        wot = ResizeFileBoxWorkOrder(box_id=box_id)
        headers = self._auth_header(wot)
        body = {"version": version, "max_size": max_size}
        response = await self._client.patch(
            f"{self._ucs_url}/boxes/{box_id}",
            headers=headers,
            json=body,
            timeout=HTTPX_TIMEOUT,
        )
        if response.status_code == 204:
            return

        if response.status_code == 409:
            self._raise_for_409(
                response=response,
                body=body,
                operation="resize",
                box_id=box_id,
            )
        log.error(
            "Error resizing FileUploadBox ID %s in external service.",
            box_id,
            extra={
                "status_code": response.status_code,
                "response_text": response.text,
            },
        )
        raise self.OperationError("Failed to resize FileUploadBox.")

    async def delete_file_upload(self, *, box_id: UUID4, file_id: UUID4) -> None:
        """Delete a FileUpload from a FileUploadBox in the owning service.

        Raises:
            OperationError if there's a problem with the operation.
        """
        wot = DeleteFileUploadWorkOrder(box_id=box_id, file_id=file_id)
        headers = self._auth_header(wot)
        response = await self._client.delete(
            f"{self._ucs_url}/boxes/{box_id}/uploads/{file_id}",
            headers=headers,
            timeout=HTTPX_TIMEOUT,
        )
        if response.status_code == 204:
            return

        extra: dict[str, Any] = {
            "box_id": box_id,
            "file_id": file_id,
            "response_text": response.text,
            "status_code": response.status_code,
        }

        if response.status_code == 404:
            log.error(
                "FileUploadBox %s not found in external service when attempting to"
                + " delete FileUpload %s. The RDUB and FUB states may be out of sync.",
                box_id,
                file_id,
                extra=extra,
            )
            raise self.OperationError(
                f"FileUploadBox {box_id} was not found in the external service."
            )

        if response.status_code == 409:
            self._raise_for_409(
                response=response,
                body={},
                operation="delete file from",
                box_id=box_id,
            )

        log.error(
            "Error deleting FileUpload %s from FileUploadBox %s.",
            file_id,
            box_id,
            extra=extra,
        )
        raise self.OperationError(f"Failed to delete file upload {file_id}.")

    async def delete_file_upload_box(self, *, box_id: UUID4, version: int) -> None:
        """Delete a FileUploadBox and all its FileUploads in the owning service.

        A 404 (box not found) is treated as success so that retries after a partial
        deletion are idempotent.

        Raises:
            FUBVersionError if the remote box version differs from `version`.
            OperationError if there's any other problem with the operation.
        """
        wot = DeleteFileBoxWorkOrder(box_id=box_id)
        headers = self._auth_header(wot)
        response = await self._client.delete(
            f"{self._ucs_url}/boxes/{box_id}",
            headers=headers,
            params={"version": version},
            timeout=HTTPX_TIMEOUT,
        )
        if response.status_code == 204:
            return

        extra: dict[str, Any] = {
            "box_id": box_id,
            "version": version,
            "status_code": response.status_code,
            "response_text": response.text,
        }

        if response.status_code == 404:
            log.warning(
                "FileUploadBox %s was already absent from the external service when"
                + " attempting to delete it. Treating it as a success.",
                box_id,
                extra=extra,
            )
            return

        if response.status_code == 409:
            self._raise_for_409(
                response=response,
                body={},
                operation="delete",
                box_id=box_id,
            )

        log.error(
            "Error deleting FileUploadBox %s in external service.",
            box_id,
            extra=extra,
        )
        raise self.OperationError(f"Failed to delete FileUploadBox {box_id}.")
