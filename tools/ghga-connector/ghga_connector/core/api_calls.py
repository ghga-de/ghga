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
from io import BytesIO
from typing import Optional

import pycurl

from .main import BadResponseCodeError, NoS3AccessMethod, RequestFailedError


def upload_api_call(api_url: str, file_id: str) -> str:
    """
    Perform a RESTful API call to retrieve a presigned upload URL
    """

    # build url
    url = api_url + "/presigned_post/" + file_id

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
    except pycurl.error as pycurl_error:
        raise RequestFailedError(url) from pycurl_error

    status_code = curl.getinfo(pycurl.RESPONSE_CODE)
    curl.close()

    if status_code != 200:
        raise BadResponseCodeError(url, status_code)

    dictionary = json.loads(data.getvalue())
    response_url = dictionary["presigned_post"]

    return response_url


def download_api_call(api_url: str, file_id: str) -> Optional[str]:

    """
    Perform a RESTful API call to retrieve a presigned download URL
    """

    # build url
    url = api_url + "/objects/" + file_id

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
    except pycurl.error as pycurl_error:
        raise RequestFailedError(url) from pycurl_error

    status_code = curl.getinfo(pycurl.RESPONSE_CODE)
    curl.close()

    if status_code != 200:
        if status_code != 202:
            raise BadResponseCodeError(url, status_code)
        return None

    dictionary = json.loads(data.getvalue())

    download_url = None

    access_methods = dictionary["access_methods"]
    for access_method in access_methods:
        if access_method["type"] == "s3":
            download_url = access_method["access_url"]["url"]

    if download_url is None:
        raise NoS3AccessMethod(url)

    return download_url


def confirm_api_call(api_url, file_id):
    """
    Perform a RESTful API call to request a confirmation of the upload of a specific file
    """

    # build url

    url = api_url + "/confirm_upload/" + file_id

    post_data = {"state": "registered"}
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
    except pycurl.error as pycurl_error:
        raise RequestFailedError(url) from pycurl_error

    status_code = curl.getinfo(pycurl.RESPONSE_CODE)
    curl.close()

    if status_code != 204:
        raise BadResponseCodeError(url, status_code)
