# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""
Contains API calls to the API of the GHGA Storage implementation
"""

import json
from enum import Enum
from time import sleep
from typing import Dict, Iterator, List, Optional, Tuple, Union

import requests

from ghga_connector.core.constants import MAX_PART_NUMBER
from ghga_connector.core.message_display import AbstractMessageDisplay

from .exceptions import (
    BadResponseCodeError,
    MaxPartNoExceededError,
    MaxWaitTimeExceeded,
    NoS3AccessMethod,
    NoUploadPossibleError,
    RequestFailedError,
    RetryTimeExpectedError,
    UploadNotRegisteredError,
)

# Constants for clarity of return values
NO_DOWNLOAD_URL = None
NO_FILE_SIZE = None
NO_RETRY_TIME = None


class UploadStatus(str, Enum):
    """
    Enum for the possible statuses of an upload attempt.
    """

    ACCEPTED = "accepted"
    CANCELLED = "cancelled"
    FAILED = "failed"
    PENDING = "pending"
    REJECTED = "rejected"
    UPLOADED = "uploaded"


def initiate_multipart_upload(api_url: str, file_id: str) -> Tuple[str, int]:
    """
    Perform a RESTful API call to initiate a multipart upload
    Returns an upload id and a part size
    """

    # build url and headers
    url = f"{api_url}/files/{file_id}/uploads"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # Make function call to get upload url
    try:
        response = requests.post(url=url, headers=headers)
    except requests.exceptions.RequestException as request_error:
        raise RequestFailedError(url) from request_error

    status_code = response.status_code
    if status_code != 200:
        if status_code == 403:
            raise NoUploadPossibleError(file_id=file_id)
        raise BadResponseCodeError(url, status_code)

    response_body = response.json()

    return response_body["upload_id"], int(response_body["part_size"])


def get_part_upload_url(*, api_url: str, upload_id: str, part_no: int):
    """
    Get a presigned url to upload a specific part
    """

    # build url and headers
    url = f"{api_url}/uploads/{upload_id}/parts/{part_no}/signed_posts"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # Make function call to get upload url
    try:
        response = requests.post(url=url, headers=headers)
    except requests.exceptions.RequestException as request_error:
        raise RequestFailedError(url) from request_error

    status_code = response.status_code
    if status_code != 200:
        raise BadResponseCodeError(url, status_code)

    response_body = response.json()
    presigned_post = response_body["presigned_post"]

    return presigned_post


def get_part_upload_urls(
    *,
    api_url: str,
    upload_id: str,
    from_part: int = 1,
    get_url_func=get_part_upload_url,
) -> Iterator[str]:
    """
    For a specific mutli-part upload identified by the `upload_id`, it returns an
    iterator to iterate through file parts and obtain the corresponding upload urls.

    By default it start with the first part but you may also start from a specific part
    in the middle of the file using the `from_part` argument. This might be useful to
    resume an interrupted upload process.

    Please note: the upload corresponding to the `upload_id` must have already been
    initiated.

    `get_url_func` only for testing purposes.
    """

    for part_no in range(from_part, MAX_PART_NUMBER + 1):
        yield get_url_func(api_url=api_url, upload_id=upload_id, part_no=part_no)

    raise MaxPartNoExceededError()


def patch_multipart_upload(
    api_url: str, upload_id: str, upload_status: UploadStatus
) -> None:
    """
    Set the status of a specific upload attempt.
    The API accepts "uploaded" or "accepted",
    if the upload_id is currently set to "pending"
    """

    # build url and headers
    url = f"{api_url}/uploads/{upload_id}"
    headers = {"Accept": "*/*", "Content-Type": "application/json"}
    post_data = {"upload_status": upload_status}
    serialized_data = json.dumps(post_data)

    try:
        response = requests.patch(url=url, headers=headers, data=serialized_data)
    except requests.exceptions.RequestException as request_error:
        raise RequestFailedError(url) from request_error

    status_code = response.status_code
    if status_code != 204:
        raise BadResponseCodeError(url, status_code)


def get_pending_uploads(api_url: str, file_id: str) -> Optional[List[Dict]]:
    """
    Get all multipart-uploads of a specific file which are currently pending.
    The number of multipart uploads can either be 0 or 1
    Returns either the upload_id and part_size of the pending upload, or None
    """

    # build url and headers
    url = f"{api_url}/files/{file_id}/uploads"
    params = {"upload_status": "pending"}
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    try:
        response = requests.get(url=url, headers=headers, params=params)
    except requests.exceptions.RequestException as request_error:
        raise RequestFailedError(url) from request_error

    status_code = response.status_code
    if status_code != 200:
        raise BadResponseCodeError(url, status_code)

    pending_uploads: list = response.json()
    if len(pending_uploads) == 0:
        return None

    return pending_uploads


def download_api_call(
    api_url: str, file_id: str
) -> Union[Tuple[None, None, int], Tuple[str, int, None]]:
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

    # build url and headers
    url = f"{api_url}/objects/{file_id}"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    # Make function call to get upload url
    try:
        response = requests.get(url=url, headers=headers)
    except requests.exceptions.RequestException as request_error:
        raise RequestFailedError(url) from request_error

    status_code = response.status_code
    if status_code != 200:
        if status_code != 202:
            raise BadResponseCodeError(url, status_code)

        headers = response.headers
        if "retry-after" not in headers:
            raise RetryTimeExpectedError(url)

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
        raise NoS3AccessMethod(url)

    return download_url, file_size, NO_RETRY_TIME


def start_multipart_upload(api_url: str, file_id: str) -> Tuple[str, int]:
    """Try to initiate a multipart upload. If it fails, try to cancel the current upload
    can and then try to initiate a multipart upload again."""

    try:
        multipart_upload = initiate_multipart_upload(api_url=api_url, file_id=file_id)
        return multipart_upload
    except NoUploadPossibleError as error:
        pending_uploads = get_pending_uploads(api_url=api_url, file_id=file_id)
        if pending_uploads is None:
            raise error
    except Exception as error:
        raise error

    for upload in pending_uploads:
        upload_id = upload[0]
        try:
            patch_multipart_upload(
                api_url=api_url,
                upload_id=upload_id,
                upload_status=UploadStatus.CANCELLED,
            )

        except Exception as error:
            raise UploadNotRegisteredError(upload_id=upload_id) from error

    try:
        multipart_upload = initiate_multipart_upload(api_url=api_url, file_id=file_id)
    except Exception as error:
        raise error

    return multipart_upload


def await_download_url(
    api_url: str,
    file_id: str,
    max_wait_time: int,
    message_display: AbstractMessageDisplay,
) -> Tuple[str, int]:
    """Wait until download URL can be generated.
    Returns a tuple with two elements:
        1. the download url
        2. the file size in bytes
    """

    # get the download_url, wait if needed
    wait_time = 0
    while wait_time < max_wait_time:
        try:
            response_body = download_api_call(api_url, file_id)
        except BadResponseCodeError as error:
            message_display.failure(
                "The request was invalid and returnd a wrong HTTP status code."
            )
            raise error
        except RequestFailedError as error:
            message_display.failure("The request has failed.")
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

    raise MaxWaitTimeExceeded(max_wait_time)
