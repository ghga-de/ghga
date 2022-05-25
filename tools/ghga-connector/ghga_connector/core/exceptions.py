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

from ghga_connector.core.constants import MAX_PART_NUMBER


class GHGAConnectorException(BaseException):
    """
    Base Exception for all custom-thrown exceptions.
    Indicates expected behaviour such as user error or unstable connections
    """


class RetryTimeExpectedError(RuntimeError, GHGAConnectorException):
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


class NoS3AccessMethod(RuntimeError, GHGAConnectorException):
    """Thrown, when a request returns the desired response code, but no S3 Access Method"""

    def __init__(self, url: str):
        message = f"The request to {url} did not return an S3 Access Method."
        super().__init__(message)


class FileNotRegisteredError(RuntimeError, GHGAConnectorException):
    """Thrown, when a request for a file returns a 404 error."""

    def __init__(self, file_id: str):
        message = (
            f"The request for the file {file_id} failed, "
            "because this file id does not exist."
        )
        super().__init__(message)


class UploadNotRegisteredError(RuntimeError, GHGAConnectorException):
    """Thrown, when a request for a multipart upload returns a 404 error."""

    def __init__(self, upload_id: str):
        message = (
            f"The request for the upload with the id '{upload_id}' failed, "
            "because this upload does not exist."
        )
        super().__init__(message)


class BadResponseCodeError(RuntimeError):
    """Thrown, when a request returns an unexpected response code (e.g. 500)"""

    def __init__(self, url: str, response_code: int):
        message = f"The request to {url} failed with response code {response_code}"
        super().__init__(message)


class UploadDoesNotExistError(RuntimeError, GHGAConnectorException):
    """Thrown, when a request to patch an upload fails with response code 404"""

    def __init__(self, upload_id: str):
        message = f"The upload with the id '{upload_id}' does not exists."
        super().__init__(message)


class NoUploadPossibleError(RuntimeError, GHGAConnectorException):
    """Thrown, when a multipart upload currently can't be started (response code 400)"""

    def __init__(self, file_id: str):
        message = (
            f"It is not possible to start a multipart upload for file with id '{file_id}', "
            "because this download is already pending or has been accepted."
        )
        super().__init__(message)


class UserHasNoAccess(RuntimeError, GHGAConnectorException):
    """
    Thrown, when a User does not have the credentials for a
    specific file id (response code 403)
    """

    def __init__(self, file_id: str):
        message = f"This user is not registered as data submitter for the file with id '{file_id}'."
        super().__init__(message)


class MaxWaitTimeExceeded(RuntimeError, GHGAConnectorException):
    """Thrown, when the specified wait time for getting a download url has been exceeded."""

    def __init__(self, max_wait_time: int):
        message = f"Exceeded maximum wait time of {max_wait_time} seconds."
        super().__init__(message)


class MaxRetriesReached(RuntimeError, GHGAConnectorException):
    """Thrown, when the specified number of retries has been exceeded."""

    def __init__(self, part_no: int):
        message = f"Exceeded maximum retries for part number '{part_no}'."
        super().__init__(message)


class MaxPartNoExceededError(RuntimeError):
    """
    Thrown requesting a part number larger than the maximally possible number of parts.

    This exception is a bug.
    """

    def __init__(
        self,
    ):
        message = f"No more than ({MAX_PART_NUMBER}) file parts can be up-/downloaded."
        super().__init__(message)
