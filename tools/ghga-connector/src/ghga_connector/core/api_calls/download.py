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

"""This file contains all api calls related to uploading files"""

import base64
from collections.abc import Iterator
from time import sleep
from typing import Union

import httpx
from requests.structures import CaseInsensitiveDict

from ghga_connector.core import exceptions
from ghga_connector.core.api_calls.work_package import WorkPackageAccessor
from ghga_connector.core.client import httpx_client
from ghga_connector.core.constants import TIMEOUT
from ghga_connector.core.http_translation import ResponseExceptionTranslator
from ghga_connector.core.message_display import AbstractMessageDisplay

# Constants for clarity of return values
NO_DOWNLOAD_URL = None
NO_FILE_SIZE = None
NO_RETRY_TIME = None


def get_download_url(
    *, file_id: str, work_package_accessor: WorkPackageAccessor
) -> Union[tuple[None, None, int], tuple[str, int, None]]:
    """
    Perform a RESTful API call to retrieve a presigned download URL.
    Returns:
        A tuple of three elements:
            1. the download url
            2. the file size (in bytes)
            3. the retry-time
        If the download url is not available yet, the first two elements are None and
        the retry-time is set.
        Otherwise, only the last element is None while the others are set.
    """
    # fetch a work order token
    decrypted_token = work_package_accessor.get_work_order_token(file_id=file_id)

    # build url and headers
    url = f"{work_package_accessor.dcs_api_url}/objects/{file_id}"
    headers = CaseInsensitiveDict(
        {
            "Accept": "application/json",
            "Authorization": f"Bearer {decrypted_token}",
            "Content-Type": "application/json",
        }
    )

    # Make function call to get download url
    try:
        with httpx_client() as client:
            response = client.get(url=url, headers=headers, timeout=TIMEOUT)
    except httpx.RequestError as request_error:
        exceptions.raise_if_connection_failed(request_error=request_error, url=url)
        raise exceptions.RequestFailedError(url=url) from request_error

    status_code = response.status_code
    if status_code != 200:
        if status_code == 403:
            content = response.json()
            # handle both normal and httpyexpect 403 response
            if "description" in content:
                cause = content["description"]
            else:
                cause = content["detail"]
            raise exceptions.UnauthorizedAPICallError(url=url, cause=cause)
        if status_code != 202:
            raise exceptions.BadResponseCodeError(url=url, response_code=status_code)

        headers = response.headers
        if "retry-after" not in headers:
            raise exceptions.RetryTimeExpectedError(url=url)

        return (NO_DOWNLOAD_URL, NO_FILE_SIZE, int(headers["retry-after"]))

    # look for an access method of type s3 in the response:
    response_body = response.json()
    download_url = None
    access_methods = response_body["access_methods"]
    for access_method in access_methods:
        if access_method["type"] == "s3":
            download_url = access_method["access_url"]["url"]
            file_size = response_body["size"]
            break

    if download_url is None:
        raise exceptions.NoS3AccessMethodError(url=url)

    return download_url, file_size, NO_RETRY_TIME


def get_download_urls(
    *, file_id: str, work_package_accessor: WorkPackageAccessor
) -> Iterator[Union[tuple[None, None, int], tuple[str, int, None]]]:
    """
    For a specific mutli-part upload identified by the `file_id`, it returns an
    iterator to obtain download_urls.
    """
    while True:
        yield get_download_url(
            file_id=file_id, work_package_accessor=work_package_accessor
        )


def await_download_url(
    *,
    file_id: str,
    max_wait_time: int,
    message_display: AbstractMessageDisplay,
    work_package_accessor: WorkPackageAccessor,
) -> tuple[str, int]:
    """Wait until download URL can be generated.
    Returns a tuple with two elements:
        1. the download url
        2. the file size in bytes
    """
    # get the download_url, wait if needed
    wait_time = 0
    while wait_time < max_wait_time:
        try:
            response_body = get_download_url(
                file_id=file_id,
                work_package_accessor=work_package_accessor,
            )
        except exceptions.BadResponseCodeError as error:
            message_display.failure(
                "The request was invalid and returned a bad HTTP status code."
            )
            raise error
        except exceptions.RequestFailedError as error:
            message_display.failure("The request failed.")
            raise error

        if response_body[0] is not None:
            download_url: str = response_body[0]
            file_size: int = response_body[1]
            return (download_url, file_size)

        retry_time: int = response_body[2]

        wait_time += retry_time
        message_display.display(
            f"File staging, will try to download again in {retry_time} seconds"
        )
        sleep(retry_time)

    raise exceptions.MaxWaitTimeExceededError(max_wait_time=max_wait_time)


def get_file_header_envelope(
    file_id: str, work_package_accessor: WorkPackageAccessor
) -> bytes:
    """
    Perform a RESTful API call to retrieve a file header envelope.
    Returns:
        The file header envelope (bytes object)
    """
    # fetch a work order token
    decrypted_token = work_package_accessor.get_work_order_token(file_id=file_id)

    # build url and headers
    url = f"{work_package_accessor.dcs_api_url}/objects/{file_id}/envelopes"

    headers = CaseInsensitiveDict(
        {
            "Accept": "application/json",
            "Authorization": f"Bearer {decrypted_token}",
            "Content-Type": "application/json",
        }
    )

    # Make function call to get download url
    try:
        with httpx_client() as client:
            response = client.get(url=url, headers=headers, timeout=TIMEOUT)
    except httpx.RequestError as request_error:
        raise exceptions.RequestFailedError(url=url) from request_error

    status_code = response.status_code

    if status_code == 200:
        return base64.b64decode(response.content)

    # For now unauthorized responses are not handled by httpyexpect
    if status_code == 403:
        content = response.json()
        # handle both normal and httpyexpect 403 response
        if "description" in content:
            cause = content["description"]
        else:
            cause = content["detail"]
        raise exceptions.UnauthorizedAPICallError(url=url, cause=cause)

    spec = {
        404: {
            "envelopeNotFoundError": lambda: exceptions.EnvelopeNotFoundError(
                file_id=file_id
            ),
            "noSuchObject": lambda: exceptions.FileNotRegisteredError(file_id=file_id),
        },
        500: {"externalAPIError": exceptions.ExternalApiError},
    }

    ResponseExceptionTranslator(spec=spec).handle(response=response)
    raise exceptions.BadResponseCodeError(url=url, response_code=status_code)
