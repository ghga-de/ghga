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
#

"""Custom Exceptions."""

from pathlib import Path

import requests
import urllib3.exceptions

from ghga_connector.core.constants import MAX_PART_NUMBER


class AbortBatchProcessError(RuntimeError):
    """Thrown when user selected to not proceed with batch proccesing"""

    def __init__(self):
        message = "Aborting batch process"
        super().__init__(message)


class DirectoryDoesNotExistError(RuntimeError):
    """Thrown, when the specified directory does not exist."""

    def __init__(self, *, output_dir: Path):
        message = f"The directory {output_dir} does not exist."
        super().__init__(message)


class FileAlreadyExistsError(RuntimeError):
    """Thrown, when the specified file already exists."""

    def __init__(self, *, output_file: str):
        message = f"The file {output_file} does already exist."
        super().__init__(message)


class FileAlreadyEncryptedError(RuntimeError):
    """Thrown, when the specified file is already encrypted."""

    def __init__(self, *, file_path: Path):
        message = f"The file {file_path} is already Crypt4GH encrypted."
        super().__init__(message)


class FileDoesNotExistError(RuntimeError):
    """Thrown, when the specified file does not exist."""

    def __init__(self, *, file_path: Path):
        message = f"The file {file_path} does not exist."
        super().__init__(message)


class PubKeyFileDoesNotExistError(RuntimeError):
    """Thrown, when the specified public key file does not exist."""

    def __init__(self, *, pubkey_path: Path):
        message = f"The public key file {pubkey_path} does not exist."
        super().__init__(message)


class PubkeyMismatchError(RuntimeError):
    """
    Thrown when the user public key announced in the submission metadata retrieved from
    the work package service does not match the user public key provided to the connector
    """

    def __init__(self):
        message = "Provided user public key does not match announced user public key."
        super().__init__(message)


class PrivateKeyFileDoesNotExistError(RuntimeError):
    """Thrown, when the specified private key file does exist."""

    def __init__(self, *, private_key_path: Path):
        message = f"The private key file {private_key_path} does not exist."
        super().__init__(message)


class ApiNotReachableError(RuntimeError):
    """Thrown, when the api is not reachable."""

    def __init__(self, *, api_url: str):
        message = f"The url {api_url} is currently not reachable."
        super().__init__(message)


class RetryTimeExpectedError(RuntimeError):
    """Thrown, when a request didn't contain a retry time even though it was expected."""

    def __init__(self, *, url: str):
        message = (
            f"No `Retry-After` header in response from server following the url: {url}"
        )
        super().__init__(message)


class RequestFailedError(RuntimeError):
    """Thrown, when a request fails without returning a response code"""

    def __init__(self, *, url: str):
        message = f"The request to {url} failed."
        super().__init__(message)


class NoS3AccessMethodError(RuntimeError):
    """Thrown, when a request returns the desired response code, but no S3 Access
    Method"""

    def __init__(self, *, url: str):
        message = f"The request to {url} did not return an S3 Access Method."
        super().__init__(message)


class FileNotRegisteredError(RuntimeError):
    """Thrown, when a request for a file returns a 404 error."""

    def __init__(self, *, file_id: str):
        message = (
            f"The request for the file {file_id} failed, "
            "because this file id does not exist."
        )
        super().__init__(message)


class UploadNotRegisteredError(RuntimeError):
    """Thrown, when a request for a multipart upload returns a 404 error."""

    def __init__(self, *, upload_id: str):
        message = (
            f"The request for the upload with the id '{upload_id}' failed, "
            "because this upload does not exist."
        )
        super().__init__(message)


class BadResponseCodeError(RuntimeError):
    """Thrown, when a request returns an unexpected response code (e.g. 500)"""

    def __init__(self, *, url: str, response_code: int):
        self.response_code = response_code
        message = f"The request to {url} failed with response code {response_code}."
        super().__init__(message)


class NoUploadPossibleError(RuntimeError):
    """Thrown, when a multipart upload currently can't be started (response code 400)"""

    def __init__(self, *, file_id: str):
        message = (
            "It is not possible to start a multipart upload for file with id"
            + f" '{file_id}', because this download is already pending or has been"
            + " accepted."
        )
        super().__init__(message)


class DownloadFinalizationError(RuntimeError):
    """
    Thrown when a downloaded file cannot be moved to its final location, as another file
    already exists at that location that was not present at the beginning of the batch process
    """

    def __init__(self, *, file_path: Path):
        message = (
            "Cannot move downloaded file to its final location as another file "
            + f"unexpectedly exists at {file_path}"
        )
        super().__init__(message)


class UserHasNoUploadAccessError(RuntimeError):
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


class UserHasNoFileAccessError(RuntimeError):
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


class CantChangeUploadStatusError(RuntimeError):
    """
    Thrown when the upload status of a file can't be set to the requested status
    (response code 400)
    """

    def __init__(self, *, upload_id: str, upload_status: str):
        message = f"The upload with id '{upload_id}' can't be set to '{upload_status}'."
        super().__init__(message)


class MaxWaitTimeExceededError(RuntimeError):
    """Thrown, when the specified wait time for getting a download url has been
    exceeded."""

    def __init__(self, *, max_wait_time: int):
        message = f"Exceeded maximum wait time of {max_wait_time} seconds."
        super().__init__(message)


class MaxRetriesReachedError(RuntimeError):
    """Thrown, when the specified number of retries has been exceeded."""

    def __init__(self, *, url: str, reason: str):
        message = f"Exceeded maximum retries for '{url}' due to: {reason}."
        super().__init__(message)


class MaxPartNoExceededError(RuntimeError):
    """
    Thrown requesting a part number larger than the maximally possible number of parts.

    This exception is a bug.
    """

    def __init__(self):
        message = f"No more than ({MAX_PART_NUMBER}) file parts can be up-/downloaded."
        super().__init__(message)


def raise_if_max_retries(request_error: requests.exceptions.RequestException, url: str):
    """
    Check if request exception is caused by hitting max retries and raise accordingly
    """
    if isinstance(request_error, requests.exceptions.ConnectionError):
        if request_error.args and isinstance(
            request_error.args[0], urllib3.exceptions.MaxRetryError
        ):
            max_retry_error = request_error.args[0]
            raise MaxRetriesReachedError(
                url=url, reason=str(max_retry_error.reason)
            ) from max_retry_error


class EnvelopeNotFoundError(RuntimeError):
    """Thrown, when the envelope requested for a file could not be retrieved"""

    def __init__(self, *, file_id: str):
        message = f"The request for an envelope for the file with ID {file_id} failed."
        super().__init__(message)


class ExternalApiError(RuntimeError):
    """Thrown, when the services request to an external API failed"""

    def __init__(self):
        message = "The service was unable to contact an external API."
        super().__init__(message)


class InvalidWorkPackageToken(RuntimeError):
    """Thrown, when the work package string pasted by the user could not be parsed"""

    def __init__(self, *, tries: int):
        message = f"Parsing of the work package string failed {tries} times."
        super().__init__(message)


class NoWorkPackageAccessError(RuntimeError):
    """
    Thrown when the given auth token does not provide access for
    a specific work package id (response code 403)
    """

    def __init__(self, *, work_package_id: str):
        message = (
            "This auth token is not valid "
            f"for the work package with the id '{work_package_id}'."
        )
        super().__init__(message)


class InvalidWPSResponseError(RuntimeError):
    """
    Thrown when communication with the Work Package Service returns an unexpected response.
    This should be used instead of BadResponseError when handling WPS results to differntiate
    """

    def __init__(self, *, url: str, response_code: int):
        self.response_code = response_code
        message = (
            f"The request to the WPS at {url} failed with an unexpected response code"
            + f" of {response_code}."
        )
        super().__init__(message)


class UnauthorizedAPICallError(RuntimeError):
    """
    Thrown when a 403 is returned from a call requiring a work order token for authorization
    """

    def __init__(self, *, url: str, cause: str):
        message = f"Could not authorize call to {url}: {cause}"
        super().__init__(message)
