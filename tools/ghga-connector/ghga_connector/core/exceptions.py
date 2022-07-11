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

from pathlib import Path

from ghga_connector.core.constants import MAX_PART_NUMBER


class KnownError(Exception):
    """
    Base Exception for all custom-thrown exceptions.
    Indicates expected behaviour such as user error or unstable connections
    """


class UnkownError(Exception):
    """
    Indicates unexpected behaviour such as bug in this package that are not caused by
    usage errors.
    Please note, all exceptions that do not inherit from `KownError` MUST be considered
    unkown. This exception is just to explicitly state the unkown character of the error
    in the code.
    """


class FatalError(Exception):
    """
    Base Exception for all exceptions that should not trigger retry logic
    """


class CollectiveError(RuntimeError, KnownError):
    """
    An error that can have one or more direct causes.
    Please note, this is different from using the `raise ... from ...` statement since
    the statement only allows to capture one direct cause.
    """

    def __init__(self, *, base_message: str, causes: list[KnownError]):

        if len(causes) < 1:
            raise TypeError(
                "Collective error must receive at least one causal error but zero were"
                + " given"
            )

        self.causes = causes
        message = (
            f"{base_message}\nThis error was caused by following prior exceptions:"
        )

        for i, cause in enumerate(causes):
            if not isinstance(cause, KnownError):
                raise TypeError(
                    "A causal error of an error collection was unkown."
                ) from cause

            message += f"\n  {i+1}: {cause}"
        super().__init__(message)


class DirectoryDoesNotExistError(RuntimeError, KnownError):
    """Thrown, when the specified directory does not exist."""

    def __init__(self, *, output_dir: Path):
        message = f"The directory {output_dir} does not exist."
        super().__init__(message)


class FileAlreadyExistsError(RuntimeError, KnownError):
    """Thrown, when the specified file already exists."""

    def __init__(self, *, output_file: str):
        message = f"The file {output_file} does already exist."
        super().__init__(message)


class FileDoesNotExistError(RuntimeError, KnownError):
    """Thrown, when the specified file already exists."""

    def __init__(self, *, file_path: Path):
        message = f"The file {file_path} does not exist."
        super().__init__(message)


class ApiNotReachableError(RuntimeError, KnownError):
    """Thrown, when the api is not reachable."""

    def __init__(self, *, api_url: str):
        message = f"The url {api_url} is currently not reachable."
        super().__init__(message)


class RetryAbortError(CollectiveError, FatalError):
    """
    Raised on encountering a FatalError in the WithRetry decorator.
    Information about all preceding exceptions encountered before the FatalError is
    attached.
    """

    def __init__(self, *, func_name: str, causes: list[KnownError]):
        base_message = f"'{func_name}' raised a FatalError."
        super().__init__(base_message=base_message, causes=causes)


class RetryTimeExpectedError(RuntimeError, KnownError, FatalError):
    """Thrown, when a request didn't contain a retry time even though it was expected."""

    def __init__(self, *, url: str):
        message = (
            f"No `Retry-After` header in response from server following the url: {url}"
        )
        super().__init__(message)


class RequestFailedError(RuntimeError, KnownError):
    """Thrown, when a request fails without returning a response code"""

    def __init__(self, *, url: str):
        message = f"The request to {url} failed."
        super().__init__(message)


class NoS3AccessMethodError(RuntimeError, KnownError, FatalError):
    """Thrown, when a request returns the desired response code, but no S3 Access
    Method"""

    def __init__(self, *, url: str):
        message = f"The request to {url} did not return an S3 Access Method."
        super().__init__(message)


class FileNotRegisteredError(RuntimeError, KnownError, FatalError):
    """Thrown, when a request for a file returns a 404 error."""

    def __init__(self, *, file_id: str):
        message = (
            f"The request for the file {file_id} failed, "
            "because this file id does not exist."
        )
        super().__init__(message)


class UploadNotRegisteredError(RuntimeError, KnownError, FatalError):
    """Thrown, when a request for a multipart upload returns a 404 error."""

    def __init__(self, *, upload_id: str):
        message = (
            f"The request for the upload with the id '{upload_id}' failed, "
            "because this upload does not exist."
        )
        super().__init__(message)


class BadResponseCodeError(RuntimeError, FatalError):
    """Thrown, when a request returns an unexpected response code (e.g. 500)"""

    def __init__(self, *, url: str, response_code: int):
        self.response_code = response_code
        message = f"The request to {url} failed with response code {response_code}"
        super().__init__(message)


class NoUploadPossibleError(RuntimeError, KnownError, FatalError):
    """Thrown, when a multipart upload currently can't be started (response code 400)"""

    def __init__(self, *, file_id: str):
        message = (
            "It is not possible to start a multipart upload for file with id"
            + f" '{file_id}', because this download is already pending or has been"
            + " accepted."
        )
        super().__init__(message)


class UserHasNoUploadAccessError(RuntimeError, KnownError, FatalError):
    """
    Thrown when a user does not have the credentials to get or change
    details of an ongoing upload with a specific upload id
    (response code 403)
    """

    def __init__(self, *, upload_id: str):
        message = (
            "This user is not registered as data submitter "
            f"for the file corresponding to the upload_id '{upload_id}'."
        )
        super().__init__(message)


class UserHasNoFileAccessError(RuntimeError, KnownError, FatalError):
    """
    Thrown when a user does not have the credentials for
    a specific file id (response code 403)
    """

    def __init__(self, *, file_id: str):
        message = (
            "This user is not registered as data submitter "
            f"for the file with the id '{file_id}'."
        )
        super().__init__(message)


class CantChangeUploadStatusError(RuntimeError, KnownError, FatalError):
    """
    Thrown when the upload status of a file can't be set to the requested status
    (response code 400)
    """

    def __init__(self, *, upload_id: str, upload_status: str):
        message = f"The upload with id '{upload_id}' can't be set to '{upload_status}'."
        super().__init__(message)


class MaxWaitTimeExceededError(RuntimeError, KnownError):
    """Thrown, when the specified wait time for getting a download url has been
    exceeded."""

    def __init__(self, *, max_wait_time: int):
        message = f"Exceeded maximum wait time of {max_wait_time} seconds."
        super().__init__(message)


class MaxRetriesReachedError(CollectiveError, FatalError):
    """Thrown, when the specified number of retries has been exceeded."""

    def __init__(self, *, func_name: str, causes: list[KnownError]):
        base_message = f"Exceeded maximum retries for '{func_name}'."
        super().__init__(base_message=base_message, causes=causes)


class MaxPartNoExceededError(RuntimeError):
    """
    Thrown requesting a part number larger than the maximally possible number of parts.

    This exception is a bug.
    """

    def __init__(self):
        message = f"No more than ({MAX_PART_NUMBER}) file parts can be up-/downloaded."
        super().__init__(message)
