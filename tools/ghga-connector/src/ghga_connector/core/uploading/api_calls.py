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

"""This module provides a client class for contacting the Upload API"""

import logging
from uuid import UUID

import httpx
from pydantic import UUID4
from tenacity import RetryError

from ghga_connector import exceptions
from ghga_connector.config import get_upload_api_url
from ghga_connector.core.api_calls.utils import is_service_healthy
from ghga_connector.core.work_package import WorkPackageClient

__all__ = ["UploadClient"]

log = logging.getLogger(__name__)


def _form_authorization_headers(work_order_token: str) -> dict[str, str]:
    """Build authorization header using supplied work order token"""
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {work_order_token}",
    }


def _check_for_request_errors(retry_error: RetryError, url: str):
    """Examine an instance of a RetryError to see if it contains an httpx.RequestError

    Raises a ConnectionFailedError if there's a ConnectError or ConnectTimeout, and
    re-raises all other httpx.RequestError types as a RequestFailedError.
    """
    exception = retry_error.last_attempt.exception()
    if exception and isinstance(exception, httpx.RequestError):
        exceptions.raise_if_connection_failed(request_error=exception, url=url)
        raise exceptions.RequestFailedError(url=url) from retry_error


class UploadClient:
    """An adapter for interacting with the Upload API and uploading files to S3."""

    def __init__(
        self, *, client: httpx.AsyncClient, work_package_client: WorkPackageClient
    ):
        self._client = client
        self._work_package_client = work_package_client
        self._upload_api_url = get_upload_api_url()

        if not is_service_healthy(self._upload_api_url):
            raise exceptions.ApiNotReachableError(api_url=self._upload_api_url)

    def _handle_bad_status_codes(
        self,
        *,
        status_code: int,
        response: httpx.Response,
        box_id: UUID4 | None = None,
        file_alias: str | None = None,
        file_id: UUID4 | None = None,
    ):
        """Translate unsuccessful status codes for calls to the Upload API"""
        work_package_id = self._work_package_client.package_id
        match status_code:
            case 400:
                raise exceptions.S3StorageError(work_package_id=work_package_id)
            case 401 | 403:
                raise exceptions.AuthorizationError()
            case 404:
                _handle_404(
                    exception_id=response.json()["exception_id"],
                    work_package_id=work_package_id,
                    file_alias=file_alias,
                    file_id=file_id,
                )
            case 409:
                _handle_409(
                    exception_id=response.json()["exception_id"],
                    work_package_id=work_package_id,
                    box_id=box_id,
                    file_alias=file_alias,
                )

        # If we didn't find a matching case, raise default error
        msg = f"Upload API returned status code {status_code}"
        raise exceptions.UnexpectedError(msg)

    async def create_file_upload(self, *, file_alias: str, file_size: int) -> UUID4:
        """Contact the Upload API to initiate a new upload for a file alias"""
        box_id = await self._work_package_client.get_package_box_id()
        create_file_wot = await self._work_package_client.get_upload_wot(
            work_type="create", box_id=box_id, file_id=None, alias=file_alias
        )

        # contact Upload API to create file upload
        url = f"{self._upload_api_url}/boxes/{box_id}/uploads"
        headers = _form_authorization_headers(create_file_wot)
        body = {"alias": file_alias, "size": file_size}

        try:
            log.debug("Requesting file upload creation at url %s", url)
            response = await self._client.post(url, headers=headers, json=body)
        except RetryError as retry_error:
            _check_for_request_errors(retry_error, url)
            response = retry_error.last_attempt.result()

        if response.status_code != 201:
            self._handle_bad_status_codes(
                status_code=response.status_code,
                response=response,
                box_id=box_id,
                file_alias=file_alias,
            )

        # Return the newly generated File ID
        file_id = UUID(response.json())
        return file_id

    async def get_part_upload_url(self, *, file_id: UUID4, part_no: int) -> str:
        """Get pre-signed S3 upload URL for a specific file part.

        Returns a pre-signed URL that can be used to upload the bytes for the specified
        part number of the specified file upload.
        """
        box_id = await self._work_package_client.get_package_box_id()  # cached
        upload_file_wot = await self._work_package_client.get_upload_wot(
            work_type="upload", box_id=box_id, file_id=file_id, alias=None
        )

        # contact Upload API to create file upload URL
        url = f"{self._upload_api_url}/boxes/{box_id}/uploads/{file_id}/parts/{part_no}"
        headers = _form_authorization_headers(upload_file_wot)

        try:
            log.debug("Getting part upload url from %s", url)
            response = await self._client.get(url, headers=headers)
        except RetryError as retry_error:
            _check_for_request_errors(retry_error, url)
            response = retry_error.last_attempt.result()

        if response.status_code != 200:
            self._handle_bad_status_codes(
                status_code=response.status_code,
                response=response,
                box_id=box_id,
                file_id=file_id,
            )

        # Return the pre-signed upload URL:
        return response.json()

    async def upload_file_part(
        self,
        *,
        file_id: UUID4,
        content: bytes,
        part_no: int,
    ) -> None:
        """Upload an encrypted file part

        Raises:
            RequestFailedError: If the request fails without returning a response code.
            UnexpectedError: If the status code is not 200.
        """
        url = await self.get_part_upload_url(file_id=file_id, part_no=part_no)

        try:
            log.debug("Uploading file part number %i for %s", part_no, str(file_id))
            response = await self._client.put(url, content=content)
        except RetryError as retry_error:
            _check_for_request_errors(retry_error, url)
            response = retry_error.last_attempt.result()

        if response.status_code != 200:
            self._handle_bad_status_codes(
                status_code=response.status_code, response=response, file_id=file_id
            )

    async def complete_file_upload(
        self, *, file_id: UUID4, unencrypted_checksum: str, encrypted_checksum: str
    ) -> None:
        """Complete a file upload"""
        box_id = await self._work_package_client.get_package_box_id()  # cached
        close_file_wot = await self._work_package_client.get_upload_wot(
            work_type="close", box_id=box_id, file_id=file_id, alias=None
        )

        url = f"{self._upload_api_url}/boxes/{box_id}/uploads/{file_id}"
        headers = _form_authorization_headers(close_file_wot)
        body = {
            "unencrypted_checksum": unencrypted_checksum,
            "encrypted_checksum": encrypted_checksum,
        }

        try:
            log.debug("Requesting file upload completion at url %s", url)
            response = await self._client.patch(url, json=body, headers=headers)
        except RetryError as retry_error:
            _check_for_request_errors(retry_error, url)
            response = retry_error.last_attempt.result()

        if response.status_code != 204:
            self._handle_bad_status_codes(
                status_code=response.status_code,
                response=response,
                box_id=box_id,
                file_id=file_id,
            )

    async def delete_file(self, *, file_id: UUID4) -> None:
        """Delete a file upload"""
        box_id = await self._work_package_client.get_package_box_id()  # cached
        delete_file_wot = await self._work_package_client.get_upload_wot(
            work_type="delete", box_id=box_id, file_id=file_id, alias=None
        )

        url = f"{self._upload_api_url}/boxes/{box_id}/uploads/{file_id}"
        headers = _form_authorization_headers(delete_file_wot)

        try:
            log.debug("Requesting file deletion at url %s", url)
            response = await self._client.delete(url, headers=headers)
        except RetryError as retry_error:
            _check_for_request_errors(retry_error, url)
            response = retry_error.last_attempt.result()

        if response.status_code != 204:
            self._handle_bad_status_codes(
                status_code=response.status_code,
                response=response,
                box_id=box_id,
                file_id=file_id,
            )


def _handle_404(
    *,
    exception_id: str,
    work_package_id: UUID4,
    file_alias: str | None,
    file_id: UUID4 | None,
):
    """Raise the proper error based on returned info about the 404

    Called from `UploadClient._handle_bad_status_codes()`.
    """
    match exception_id:
        case "boxNotFound":
            raise exceptions.InvalidBoxError(work_package_id=work_package_id)
        case "fileUploadNotFound":
            raise exceptions.InvalidFileUploadError(
                work_package_id=work_package_id,
                file_id=file_id,  # type: ignore
            )
        case "s3UploadDetailsNotFound":
            raise exceptions.S3UploadDetailsError(
                file_alias=file_alias,  # type: ignore
                work_package_id=work_package_id,
            )
        case "s3UploadNotFound":
            raise exceptions.S3UploadMissingError()


def _handle_409(
    *,
    exception_id: str,
    work_package_id: UUID4,
    box_id: UUID4 | None,
    file_alias: str | None,
):
    """Raise the proper error based on returned info about the 409.

    Called from `_handle_bad_status_codes()`.
    """
    match exception_id:
        case "lockedBox":
            raise exceptions.UploadBoxLockedError(work_package_id=work_package_id)
        case "fileUploadAlreadyExists":
            raise exceptions.UploadAlreadyExistsError(work_package_id=work_package_id)
        case "orphanedMultipartUpload":
            raise exceptions.OrphanedUploadError(
                file_alias=file_alias,  # type: ignore
                box_id=box_id,  # type: ignore
            )
