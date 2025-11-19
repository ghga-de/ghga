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
#

"""Custom Exceptions."""

from pathlib import Path

import httpx
from pydantic import UUID4

from ghga_connector.constants import MAX_PART_NUMBER


class AbortBatchProcessError(RuntimeError):
    """Thrown when user selected to not proceed with batch processing"""

    def __init__(self):
        message = "Aborting batch process"
        super().__init__(message)


class ApiNotReachableError(RuntimeError):
    """Thrown when the api is not reachable."""

    def __init__(self, *, api_url: str):
        message = f"The url '{api_url}' is currently not reachable."
        super().__init__(message)


class AuthorizationError(RuntimeError):
    """Raised when a protected endpoint returns a 401 or 403"""

    def __init__(self):
        msg = "Your request did not include valid credentials."
        super().__init__(msg)


class BadResponseCodeError(RuntimeError):
    """Thrown when a request returns an unexpected response code (e.g. 500)"""

    def __init__(self, *, url: str, response_code: int):
        self.response_code = response_code
        message = f"The request to '{url}' failed with response code {response_code}."
        super().__init__(message)


class _FileUploadError(RuntimeError):
    """Base error class for top-level errors in file upload"""

    def __init__(
        self, *, action: str, file_alias: str, reason: str, file_id: UUID4 | None = None
    ):
        # Make sure we only use one period at the end of the error message
        reason = reason.removesuffix(".")

        # Make first character of 'reason' lowercase
        reason = reason[0].lower() + reason[1:]

        # Calculate whether to show the file ID and if so format it
        file_id_portion = f" ({file_id=})" if file_id else ""
        msg = (
            f"Failed to {action} upload for file with alias {file_alias}"
            + f"{file_id_portion} because {reason}."
        )
        super().__init__(msg)


class CompleteFileUploadError(_FileUploadError):
    """Raised when there's a problem trying to complete an upload."""

    def __init__(self, *, file_alias: str, reason: str):
        super().__init__(action="complete", file_alias=file_alias, reason=reason)


class ConnectionFailedError(RuntimeError):
    """Thrown when a ConnectError or ConnectTimeout error is raised by httpx"""

    def __init__(self, *, url: str, reason: str):
        message = f"Request to '{url}' failed to connect. Reason: {reason}"
        super().__init__(message)


class CreateFileUploadError(_FileUploadError):
    """Raised when there's a problem trying to create a new FileUpload."""

    def __init__(self, *, file_alias: str, reason: str):
        super().__init__(action="initiate", file_alias=file_alias, reason=reason)


class DirectoryDoesNotExistError(RuntimeError):
    """Thrown when the specified directory does not exist."""

    def __init__(self, *, directory: Path):
        message = f"The directory '{directory}' does not exist."
        super().__init__(message)


class DownloadError(RuntimeError):
    """Raised when an error is encountered during file download"""

    def __init__(self, *, reason: str):
        message = f"Download tasks did not complete successfully. Reason: {reason}"
        super().__init__(message)


class EncryptedSizeMismatch(RuntimeError):
    """Thrown when the actual encrypted size of a file does not match the computed one"""

    def __init__(self, *, actual_encrypted_size: int, expected_encrypted_size: int):
        message = (
            "Mismatch between actual and theoretical encrypted part size:\n"
            + f"Is: {actual_encrypted_size}\n"
            + f"Should be: {expected_encrypted_size}"
        )
        super().__init__(message)


class EnvelopeNotFoundError(RuntimeError):
    """Thrown when the envelope requested for a file could not be retrieved"""

    def __init__(self, *, file_id: str):
        message = (
            f"The request for an envelope for the file with ID '{file_id}' failed."
        )
        super().__init__(message)


class FileAlreadyEncryptedError(RuntimeError):
    """Thrown when the specified file is already encrypted."""

    def __init__(self, *, file_path: Path):
        message = (
            f"The file '{file_path}' is already Crypt4GH encrypted. Provide data "
            + "without Crypt4GH encryption."
        )
        super().__init__(message)


class FileAlreadyExistsError(RuntimeError):
    """Thrown when the specified file already exists."""

    def __init__(self, *, output_file: str):
        message = f"The file '{output_file}' already exists."
        super().__init__(message)


class DeleteFileUploadError(_FileUploadError):
    """Raised when there's a problem deleting a FileUpload in the Upload API"""

    def __init__(self, *, file_alias: str, file_id: UUID4, reason: str):
        super().__init__(
            action="delete",
            file_alias=file_alias,
            file_id=file_id,
            reason=reason,
        )


class FileDoesNotExistError(RuntimeError):
    """Thrown when the specified file does not exist."""

    def __init__(self, *, file_path: Path):
        message = f"The file '{file_path}' does not exist."
        super().__init__(message)


class FileNotRegisteredError(RuntimeError):
    """Thrown when a request for a file returns a 404 error."""

    def __init__(self, *, file_id: str):
        message = (
            f"The request for the file '{file_id}' failed, "
            "because this file id does not exist."
        )
        super().__init__(message)


class GetEnvelopeError(RuntimeError):
    """Raised when fetching a header envelope fails"""


class InvalidBoxError(RuntimeError):
    """Raised when receiving a 404 from the Upload API for a given box ID"""

    def __init__(self, *, work_package_id: UUID4):
        msg = f"The upload box associated with Work Package {work_package_id} doesn't exist."
        super().__init__(msg)


class InvalidFileUploadError(RuntimeError):
    """Raised when receiving a 404 from the Upload API for a given file ID"""

    def __init__(self, *, work_package_id: UUID4, file_id: UUID4):
        msg = (
            f"The upload box associated with Work Package {work_package_id} doesn't"
            + f" have any files with the given file ID ({file_id})"
        )
        super().__init__(msg)


class InvalidWorkPackageToken(RuntimeError):
    """Thrown when the work package string pasted by the user could not be parsed"""

    def __init__(self, *, tries: int):
        message = f"Parsing of the work package string failed ({tries}) times."
        super().__init__(message)


class InvalidWorkPackageResponseError(RuntimeError):
    """
    Thrown when communication with the Work Package Service returns an unexpected response.
    This should be used instead of BadResponseError when handling Work Package API results to differentiate.
    """

    def __init__(self, *, url: str, response_code: int):
        self.response_code = response_code
        message = (
            f"The request to the Work Package API at '{url}' failed with an unexpected response code "
            + f"of {response_code}."
        )
        super().__init__(message)


class MaxPartNoExceededError(RuntimeError):
    """
    Thrown when requesting a part number larger than the maximally possible number of parts.

    This exception should never be raised and indicates a bug.
    """

    def __init__(self):
        message = f"No more than ({MAX_PART_NUMBER}) file parts can be up-/downloaded."
        super().__init__(message)


class MaxWaitTimeExceededError(RuntimeError):
    """Thrown when the specified wait time for getting a download url has been exceeded."""

    def __init__(self, *, max_wait_time: int):
        message = f"Exceeded maximum wait time of ({max_wait_time}) seconds."
        super().__init__(message)


class NoS3AccessMethodError(RuntimeError):
    """Thrown when a request returns the desired response code, but no S3 Access Method"""

    def __init__(self, *, file_id: str):
        message = (
            f"DRS object for file ID '{file_id}' did not contain an S3 Access Method."
        )
        super().__init__(message)


class NoFileAccessError(RuntimeError):
    """
    Thrown when a user does not have the credentials to access metadata or start an
    upload for a specific file identified by the given file_id (response code 403)
    """

    def __init__(self, *, file_id: str):
        message = f"You are not registered as a data submitter for the file with the id '{file_id}'."
        super().__init__(message)


class NoUploadAccessError(RuntimeError):
    """
    Thrown when a user does not have the credentials to get or change details of an
    ongoing upload identified by the given upload_id (response code 403)
    """

    def __init__(self, *, upload_id: str):
        message = (
            "You are not registered as a data submitter "
            + f"for the file corresponding to the upload_id '{upload_id}'."
        )
        super().__init__(message)


class NoWorkPackageAccessError(RuntimeError):
    """
    Thrown when the given auth token does not provide access for
    a specific work package id (response code 403)
    """

    def __init__(self, *, work_package_id: UUID4):
        message = (
            "This auth token is not valid "
            f"for the work package with the id '{work_package_id}'."
        )
        super().__init__(message)


class OrphanedUploadError(RuntimeError):
    """Raised when a multipart upload is found to be already in progress for a file
    which we are trying to create. This is a rare situation that will have to be
    resolved by the GHGA dev team if it occurs.
    """

    def __init__(self, *, file_alias: str, box_id: UUID4):
        msg = (
            "A multipart upload is already in progress for this file, but"
            + " cannot be aborted due to a system error. Please contact the GHGA Help"
            + " Desk and request manual abortion of any S3 uploads for file alias"
            + f" {file_alias} in box {box_id}."
        )
        super().__init__(msg)


class OutputPathIsNotDirectory(RuntimeError):
    """Thrown when specified output path is not a directory"""

    def __init__(self, *, directory: Path):
        message = (
            f"Path of output directory '{directory}' exists, but is not a directory."
        )
        super().__init__(message)


class PrivateKeyFileDoesNotExistError(RuntimeError):
    """Thrown when the specified private key file does exist."""

    def __init__(self, *, private_key_path: Path):
        message = f"The private key file '{private_key_path}' does not exist."
        super().__init__(message)


class PubKeyFileDoesNotExistError(RuntimeError):
    """Thrown when the specified public key file does not exist."""

    def __init__(self, *, public_key_path: Path):
        message = f"The public key file '{public_key_path}' does not exist."
        super().__init__(message)


class PubKeyMismatchError(RuntimeError):
    """
    Thrown when the user public key announced in the submission metadata retrieved from
    the work package service does not match the user public key provided to the connector
    """

    def __init__(self):
        message = "Provided public key does not match the public key from the metadata."
        super().__init__(message)


class RenameDownloadedFileError(RuntimeError):
    """
    Thrown when a downloaded file cannot be moved to its final location, as another file
    already exists at that location that was not present at the beginning of the batch process
    """

    def __init__(self, *, file_path: Path):
        message = (
            "Cannot move downloaded file to its final location as another file "
            + f"unexpectedly exists at '{file_path}'"
        )
        super().__init__(message)


class RequestFailedError(RuntimeError):
    """Thrown when a request fails without returning a response code"""

    def __init__(self, *, url: str):
        message = f"The request to '{url}' failed."
        super().__init__(message)


class RetryTimeExpectedError(RuntimeError):
    """Thrown when a request didn't contain a retry time even though it was expected."""

    def __init__(self, *, url: str):
        message = f"No `Retry-After` header in response from server following the url: '{url}'"
        super().__init__(message)


class S3StorageError(RuntimeError):
    """Raised when there's a problem in the Upload API related to the S3 storage."""

    def __init__(self, *, work_package_id: UUID4):
        msg = (
            "There was a problem with the S3 storage configuration for the upload box"
            + f" associated with Work Package {work_package_id}."
        )
        super().__init__(msg)


class S3UploadDetailsError(RuntimeError):
    """Raised when the Upload API fails to find expected details of an ongoing S3 upload"""

    def __init__(self, *, file_alias: str, work_package_id: UUID4):
        msg = (
            "The Upload API failed to find the expected information about the ongoing"
            + f" S3 upload for file alias {file_alias} in the upload box associated"
            + f" with Work Package {work_package_id}."
        )
        super().__init__(msg)


class S3UploadMissingError(RuntimeError):
    """Raised when the Upload API indicates that the S3 instance does not have record
    of a multipart upload with the ID that is stored in the Upload API's database.
    """

    def __init__(self):
        msg = "According to the Upload API, the expected multipart upload wasn't found in S3"
        super().__init__(msg)


class StartUploadError(RuntimeError):
    """Raised when an issue is encountered during the initialization of a multipart upload"""


class UnauthorizedAPICallError(RuntimeError):
    """Thrown when a 403 is returned from a call requiring authorization."""

    def __init__(self, *, url: str, cause: str):
        message = f"Could not authorize call to '{url}': {cause}"
        super().__init__(message)


class UnexpectedError(RuntimeError):
    """Raised as a catch-all when unexpected errors occur."""

    def __init__(self, info: str):
        msg = f"An unexpected error occurred: {info}"
        super().__init__(msg)


class UnexpectedRetryResponseError(RuntimeError):
    """
    Thrown when an unexpected RetryResponse was received while requesting URLs for a
    staged download
    """

    def __init__(self):
        message = (
            "An unexpected RetryResponse was received while requesting URLs for a"
            + " staged download"
        )
        super().__init__(message)


class UploadAlreadyExistsError(RuntimeError):
    """Raised when trying to create a duplicate file upload."""

    def __init__(self, *, work_package_id: UUID4):
        msg = (
            "An upload for this file alias already exists in the upload box associated"
            + f" with Work Package {work_package_id}"
        )
        super().__init__(msg)


class UploadBoxLockedError(RuntimeError):
    """Raised when trying to add/remove files for a locked FileUploadBox."""

    def __init__(self, *, work_package_id: UUID4):
        msg = (
            f"The upload box associated with work package {work_package_id} is locked."
        )
        super().__init__(msg)


class UploadFileError(_FileUploadError):
    """Raised when there's a problem trying to upload a file part."""

    def __init__(self, *, file_alias: str, reason: str):
        super().__init__(action="perform", file_alias=file_alias, reason=reason)


class UploadIdUnsetError(RuntimeError):
    """Thrown when the upload ID was not set for operations requiring a valid upload ID."""

    def __init__(self):
        message = "Upload ID is not set, upload was not initialized correctly."
        super().__init__(message)


class UploadNotRegisteredError(RuntimeError):
    """Thrown when a request for a multipart upload returns a 404 error."""

    def __init__(self, *, upload_id: str):
        message = (
            f"The request for the upload with the id '{upload_id}' failed, "
            "because this upload does not exist."
        )
        super().__init__(message)


class WellKnownValueNotFound(RuntimeError):
    """
    Thrown when a 404 is returned from a call to the well-known-value-service for a
    specific value name.
    """

    def __init__(self, *, value_name):
        message = (
            f"Unable to retrieve value of '{value_name}' from well-known-value-service"
        )
        super().__init__(message)


def raise_if_connection_failed(request_error: httpx.RequestError, url: str):
    """Check if request exception is caused by hitting max retries and raise accordingly"""
    if isinstance(request_error, (httpx.ConnectError, httpx.ConnectTimeout)):
        connection_failure = str(request_error.args[0])
        raise ConnectionFailedError(url=url, reason=connection_failure)
