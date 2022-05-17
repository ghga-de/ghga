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

"""Custom Exceptions."""


class RetryTimeExpectedError(RuntimeError):
    """Thrown, when a request didn't contain a retry time even though it was expected."""

    def __init__(self, url: str):
        message = (
            f"No `Retry-After` header in response from server following the url: {url}"
        )
        super().__init__(message)


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


class MaxWaitTimeExceeded(RuntimeError):
    """Thrown, when the specified wait time has been exceeded."""

    def __init__(self, max_wait_time: int):
        message = f"Exceeded maximum wait time of {max_wait_time} seconds."
        super().__init__(message)
