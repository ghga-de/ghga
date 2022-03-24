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

"""Main domain logic."""

import pycurl


class RequestFailedError(RuntimeError):
    """Thrown, when a request fails without returning a response code"""

    def __init__(self, url: str):
        message = f"The request to {url} failed."
        super().__init__(message)


class NoS3AccessMethod(RuntimeError):
    """Thrown, when a request returns the desired response code, but no S3 Access Method"""

    def __init__(self, url: str):
        message = f"The request to {url} did not return an S3 Access Method."
        super().__init__(message)


class BadResponseCodeError(RuntimeError):
    """Thrown, when a request returns a non-desired response code (e.g. 400)"""

    def __init__(self, url: str, response_code: int):
        message = f"The request to {url} failed with response code {response_code}"
        super().__init__(message)


def check_url(api_url, wait_time=1000) -> bool:
    """
    Checks, if an url is reachable within a certain time
    """
    curl = pycurl.Curl()
    curl.setopt(curl.URL, api_url)
    curl.setopt(curl.CONNECTTIMEOUT_MS, wait_time)
    try:
        curl.perform_rb()
    except pycurl.error:
        return False
    return True
