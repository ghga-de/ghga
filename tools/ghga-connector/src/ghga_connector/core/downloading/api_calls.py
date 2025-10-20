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

"""This module provides all API calls related to downloading files."""

import base64
from typing import Any

import httpx
from tenacity import RetryError

from ghga_connector import exceptions
from ghga_connector.config import get_download_api_url
from ghga_connector.constants import TIMEOUT_LONG
from ghga_connector.core import RetryHandler
from ghga_connector.core.api_calls.utils import modify_headers_for_cache_refresh
from ghga_connector.core.work_package import WorkPackageClient

from .structs import RetryResponse

__all__ = ["DownloadClient", "extract_download_url"]

DrsObject = dict[str, Any]


class DownloadClient:
    """An adapter for interacting with the download API and performing S3 downloads.

    This class can & should be reused for all file downloads.
    """

    def __init__(
        self, *, client: httpx.AsyncClient, work_package_client: WorkPackageClient
    ):
        self._client = client
        self._work_package_client = work_package_client
        self._download_api_url = get_download_api_url()
        self._retry_handler = RetryHandler.basic()

    async def _get_drs_object_retrieval_auth_headers(
        self, *, file_id: str, bust_cache: bool = False
    ) -> httpx.Headers:
        """Fetch work order token and headers to get object storage URL for file download"""
        decrypted_wot = await self._work_package_client.get_download_wot(
            file_id=file_id, bust_cache=bust_cache
        )
        headers = await self._work_package_client.make_auth_headers(decrypted_wot)
        return headers

    async def _retrieve_drs_object_using_params(
        self,
        *,
        url: str,
        headers: httpx.Headers,
        bust_cache: bool = False,
    ) -> RetryResponse | DrsObject:
        """
        Perform a RESTful API call to retrieve a DRS Object from the Download API.

        Returns a RetryResponse if the file exists but isn't yet available for download.
        The RetryResponse contains the time, in seconds, after which the Connector
        should try again. If the file is available for download, the DRS object is
        returned.
        """
        if bust_cache:
            modify_headers_for_cache_refresh(headers)

        try:
            response: httpx.Response = await self._retry_handler(
                fn=self._client.get,
                url=url,
                headers=headers,
                timeout=TIMEOUT_LONG,
            )
        except RetryError as retry_error:
            wrapped_exception = retry_error.last_attempt.exception()
            if isinstance(wrapped_exception, httpx.RequestError):
                exceptions.raise_if_connection_failed(
                    request_error=wrapped_exception, url=url
                )
                raise exceptions.RequestFailedError(url=url) from retry_error
            elif wrapped_exception:
                raise wrapped_exception from retry_error
            elif result := retry_error.last_attempt.result():
                response = result
            else:
                raise

        return _handle_drs_object_response(url=url, response=response)

    async def get_envelope_authorization_headers(
        self, *, file_id: str
    ) -> httpx.Headers:
        """
        Fetch download WOT and build the auth headers needed to retrieve the Crypt4GH
        envelope for the specified file.
        """
        decrypted_wot = await self._work_package_client.get_download_wot(
            file_id=file_id
        )
        headers = await self._work_package_client.make_auth_headers(decrypted_wot)
        return headers

    async def get_file_envelope(self, file_id: str) -> bytes:
        """Get the crypt4gh envelope for a given file.

        No cache refresh switch is needed here because this call only happens
        once per file.
        """
        # build url
        download_api_url = get_download_api_url()
        url = f"{download_api_url}/objects/{file_id}/envelopes"
        auth_headers = await self.get_envelope_authorization_headers(file_id=file_id)

        # Make function call to get file header envelope
        try:
            response: httpx.Response = await self._retry_handler(
                fn=self._client.get,
                headers=auth_headers,
                url=url,
            )
        except httpx.RequestError as request_error:
            raise exceptions.RequestFailedError(url=url) from request_error

        status_code = response.status_code
        match status_code:
            case 200:
                # Happy path
                return base64.b64decode(response.content)
            case 403:
                # For now unauthorized responses are not handled by httpyexpect
                # handle both normal and httpyexpect 403 response
                content = response.json()
                cause = (
                    content["description"]
                    if "description" in content
                    else content["detail"]
                )
                raise exceptions.UnauthorizedAPICallError(url=url, cause=cause)
            case 404:
                raise exceptions.FileNotRegisteredError(file_id=file_id)
            case _:
                raise exceptions.BadResponseCodeError(
                    url=url, response_code=status_code
                )

    async def get_drs_object(
        self, file_id: str, *, bust_cache: bool = False
    ) -> DrsObject | RetryResponse:
        """Gets the DRS object for the requested file ID or possibly a Retry response.

        Step 1 - obtain work order token from the Work Package API.
        Step 2 - retrieve the DRS object from the Download API using the work order token.
        Automatically retries requests if cached responses are stale.
        """
        # build URL
        download_api_url = get_download_api_url()
        url_to_get_download_url = f"{download_api_url}/objects/{file_id}"

        # Obtain work order token (headers) for the calling the Download API
        headers = await self._get_drs_object_retrieval_auth_headers(
            file_id=file_id, bust_cache=bust_cache
        )
        try:
            # Call the Download API to get the DRS object
            drs_object = await self._retrieve_drs_object_using_params(
                url=url_to_get_download_url,
                headers=headers,
                bust_cache=bust_cache,
            )
        except exceptions.UnauthorizedAPICallError:
            # Retry the above two steps while explicitly refreshing the cache if we got
            #  an error due to an expired WOT. This will trigger obtaining a fresh WOT
            #  instead of potentially using a cached version of the most recent one.
            headers = await self._get_drs_object_retrieval_auth_headers(
                file_id=file_id,
                bust_cache=True,
            )
            drs_object = await self._retrieve_drs_object_using_params(
                url=url_to_get_download_url,
                headers=headers,
                bust_cache=True,
            )

        return drs_object

    async def download_content_range(
        self, *, url: str, start: int, end: int
    ) -> tuple[int, bytes]:
        """Download a specific range of a file's content using a presigned download URL.

        Returns a tuple containing the starting position and bytes.
        """
        headers = httpx.Headers(
            {
                "Range": f"bytes={start}-{end}",
                "Cache-Control": "no-store",  # don't cache part downloads
            }
        )
        try:
            response: httpx.Response = await self._retry_handler(
                fn=self._client.get, url=url, headers=headers
            )
        except RetryError as retry_error:
            wrapped_exception = retry_error.last_attempt.exception()

            if isinstance(wrapped_exception, httpx.RequestError):
                exceptions.raise_if_connection_failed(
                    request_error=wrapped_exception, url=url
                )
                raise exceptions.RequestFailedError(url=url) from retry_error
            elif wrapped_exception:
                raise wrapped_exception from retry_error
            elif result := retry_error.last_attempt.result():
                response = result
            else:
                raise

        status_code = response.status_code

        # 200, if the full file was returned, 206 else. `match` offers no advantage here
        if status_code in (200, 206):
            return (start, response.content)

        if status_code == 403:
            raise exceptions.UnauthorizedAPICallError(
                url=url, cause="Presigned URL is likely expired."
            )

        raise exceptions.BadResponseCodeError(url=url, response_code=status_code)


def _handle_drs_object_response(
    *, url: str, response: httpx.Response
) -> DrsObject | RetryResponse:
    """Handle DRS object endpoint response from Download API.

    Returns a DRS object or RetryResponse, or raises an error.
    Cuts down McCabe complexity of `_retrieve_drs_object_using_params()` and is only
    used there.
    """
    status_code = response.status_code
    match status_code:
        case 200:
            # Success - return DRS object
            return response.json()
        case 202:
            # Retry later
            headers = response.headers
            if "retry-after" not in headers:
                raise exceptions.RetryTimeExpectedError(url=url)
            return RetryResponse(retry_after=int(headers["retry-after"]))
        case 403:
            content = response.json()
            # handle both normal and httpyexpect 403 response
            try:
                cause = content["description"]
            except KeyError:
                cause = content["detail"]
            raise exceptions.UnauthorizedAPICallError(url=url, cause=cause)
        case 404:
            # file ID will be end of url like '/objects/<file_id>'
            file_id = url.rsplit("/", 1)[1]
            raise exceptions.FileNotRegisteredError(file_id=file_id)
        case _:
            raise exceptions.BadResponseCodeError(url=url, response_code=status_code)


def extract_download_url(drs_object: DrsObject) -> str:
    """Extract the download URL from a DRS Object

    Raises:
        NoS3AccessMethodError: If the DRS object doesn't have an S3 access method.
    """
    access_methods = drs_object["access_methods"]
    for access_method in access_methods:
        if access_method["type"] == "s3":
            return access_method["access_url"]["url"]
    raise exceptions.NoS3AccessMethodError(file_id=drs_object["id"])
