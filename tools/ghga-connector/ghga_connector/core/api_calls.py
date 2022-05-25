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
from io import BytesIO
from time import sleep
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

import pycurl

from ghga_connector.core.constants import MAX_PART_NUMBER

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


def header_function_factory(headers: dict):
    """Creates a header function that updates the specified headers dict."""

    def header_function(header_line):
        """
        Function used to decode headers from HTTP Responses
        """

        # HTTP standard specifies that headers are encoded in iso-8859-1.
        header_line = header_line.decode("iso-8859-1")

        # Header lines include the first status line (HTTP/1.x ...).
        # We are going to ignore all lines that don't have a colon in them.
        # This will botch headers that are split on multiple lines...
        if ":" not in header_line:
            return

        # Break the header line into header name and value.
        name, value = header_line.split(":", 1)

        # Remove whitespace that may be present.
        # Header lines include the trailing newline, and there may be whitespace
        # around the colon.
        name = name.strip()
        value = value.strip()

        # Header names are case insensitive.
        # Lowercase name here.
        name = name.lower()

        # Now we can actually record the header name and value.
        # Note: this only works when headers are not duplicated, see below.
        headers[name] = value

    return header_function


def initiate_multipart_upload(api_url: str, file_id: str) -> Tuple[str, int]:
    """
    Perform a RESTful API call to initiate a multipart upload
    Returns an upload id and a part size
    """

    # build url
    url = f"{api_url}/files/{file_id}/uploads"

    # Make function call to get upload url
    curl = pycurl.Curl()
    data = BytesIO()
    curl.setopt(curl.URL, url)
    curl.setopt(curl.WRITEFUNCTION, data.write)

    curl.setopt(
        curl.HTTPHEADER,
        ["Accept: application/json", "Content-Type: application/json"],
    )

    curl.setopt(curl.POST, 1)
    try:
        curl.perform()
        status_code = curl.getinfo(pycurl.RESPONSE_CODE)
    except pycurl.error as pycurl_error:
        raise RequestFailedError(url) from pycurl_error
    finally:
        curl.close()

    if status_code != 200:
        if status_code == 403:
            raise NoUploadPossibleError(file_id=file_id)
        raise BadResponseCodeError(url, status_code)

    response_body = json.loads(data.getvalue())

    return response_body["upload_id"], int(response_body["part_size"])


def get_part_upload_url(*, api_url: str, upload_id: str, part_no: int):
    """
    Get a presigned url to upload a specific part
    """

    # build url
    url = f"{api_url}/uploads/{upload_id}/parts/{part_no}/signed_posts"

    # Make function call to get upload url
    curl = pycurl.Curl()
    data = BytesIO()
    curl.setopt(curl.URL, url)
    curl.setopt(curl.WRITEFUNCTION, data.write)

    curl.setopt(
        curl.HTTPHEADER,
        ["Accept: application/json", "Content-Type: application/json"],
    )

    curl.setopt(curl.POST, 1)
    try:
        curl.perform()
        status_code = curl.getinfo(pycurl.RESPONSE_CODE)
    except pycurl.error as pycurl_error:
        raise RequestFailedError(url) from pycurl_error
    finally:
        curl.close()

    if status_code != 200:
        raise BadResponseCodeError(url, status_code)

    response_body = json.loads(data.getvalue())
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
    # build url
    url = f"{api_url}/uploads/{upload_id}"

    post_data = {"upload_status": upload_status}
    postfields = json.dumps(post_data)

    curl = pycurl.Curl()
    curl.setopt(curl.URL, url)
    curl.setopt(
        curl.HTTPHEADER,
        ["Accept: */*", "Content-Type: application/json"],
    )
    curl.setopt(curl.POSTFIELDS, postfields)

    # Set to patch, since postfields sets to POST automatically
    curl.setopt(curl.CUSTOMREQUEST, "PATCH")

    try:
        curl.perform()
        status_code = curl.getinfo(pycurl.RESPONSE_CODE)
    except pycurl.error as pycurl_error:
        raise RequestFailedError(url) from pycurl_error
    finally:
        curl.close()

    if status_code != 204:
        raise BadResponseCodeError(url, status_code)


def get_pending_uploads(api_url: str, file_id: str) -> Optional[List[Dict]]:
    """
    Get all multipart-uploads of a specific file which are currently pending.
    The number of multipart uploads can either be 0 or 1
    Returns either the upload_id and part_size of the pending upload, or None
    """

    # build url
    url = f"{api_url}/files/{file_id}/uploads?upload_status=pending"

    # Make function call to get upload url
    curl = pycurl.Curl()
    data = BytesIO()
    curl.setopt(curl.URL, url)
    curl.setopt(curl.WRITEFUNCTION, data.write)

    curl.setopt(
        curl.HTTPHEADER,
        ["Accept: application/json", "Content-Type: application/json"],
    )

    # GET is the standard, but setting it here explicitely nonetheless
    curl.setopt(curl.HTTPGET, 1)
    try:
        curl.perform()
        status_code = curl.getinfo(pycurl.RESPONSE_CODE)
    except pycurl.error as pycurl_error:
        raise RequestFailedError(url) from pycurl_error
    finally:
        curl.close()

    if status_code != 200:
        raise BadResponseCodeError(url, status_code)

    list_of_uploads: list = json.loads(data.getvalue())

    if len(list_of_uploads) == 0:
        return None

    return list_of_uploads


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

    # build url
    url = f"{api_url}/objects/{file_id}"

    # Make function call to get upload url
    curl = pycurl.Curl()
    data = BytesIO()
    headers: dict[str, str] = {}
    curl.setopt(curl.URL, url)
    curl.setopt(curl.WRITEFUNCTION, data.write)
    curl.setopt(
        curl.HTTPHEADER,
        ["Accept: application/json", "Content-Type: application/json"],
    )
    curl.setopt(curl.HEADERFUNCTION, header_function_factory(headers))
    # GET is the standard, but setting it here explicitely nonetheless
    curl.setopt(curl.HTTPGET, 1)
    try:
        curl.perform()
        status_code = curl.getinfo(pycurl.RESPONSE_CODE)
    except pycurl.error as pycurl_error:
        raise RequestFailedError(url) from pycurl_error
    finally:
        curl.close()

    if status_code != 200:
        if status_code != 202:
            raise BadResponseCodeError(url, status_code)

        if "retry-after" not in headers:
            raise RetryTimeExpectedError(url)

        return (NO_DOWNLOAD_URL, NO_FILE_SIZE, int(headers["retry-after"]))

    # look for an access method of type s3 in the response:
    response_body = json.loads(data.getvalue())
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
    logger: Callable[[str], Any] = lambda x: ...,
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
            logger("The request was invalid and returnd a wrong HTTP status code.")
            raise error
        except RequestFailedError as error:
            logger("The request has failed.")
            raise error

        if response_body[0] is not None:
            download_url: str = response_body[0]
            file_size: int = response_body[1]
            return (download_url, file_size)

        retry_time: int = response_body[2]

        wait_time += retry_time
        logger(f"File staging, will try to download again in {retry_time} seconds")
        sleep(retry_time)

    raise MaxWaitTimeExceeded(max_wait_time)
