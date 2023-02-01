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

"""Main domain logic."""

import os
from pathlib import Path

import requests

from ghga_connector.core import exceptions
from ghga_connector.core.api_calls import (
    UploadStatus,
    await_download_url,
    get_part_upload_urls,
    patch_multipart_upload,
    start_multipart_upload,
)
from ghga_connector.core.constants import MAX_WAIT_TIME
from ghga_connector.core.file_operations import (
    download_file_parts,
    read_file_parts,
    upload_file_part,
)
from ghga_connector.core.message_display import AbstractMessageDisplay


def check_url(api_url, *, wait_time=1000) -> bool:
    """
    Checks, if an url is reachable within a certain time
    """
    try:
        # timeout takes seconds, was ms in curl, convert accordingly
        requests.get(url=api_url, timeout=wait_time / 1000)
    except requests.exceptions.RequestException:
        return False
    return True


def upload(  # noqa C901, pylint: disable=too-many-statements,too-many-branches
    *,
    api_url: str,
    file_id: str,
    file_path: Path,
    message_display: AbstractMessageDisplay,
    pubkey_path: Path,
) -> None:
    """
    Core command to upload a file. Can be called by CLI, GUI, etc.
    """

    if not os.path.isfile(pubkey_path):
        message_display.failure(f"The file {pubkey_path} does not exist.")
        raise exceptions.PubKeyFileDoesNotExistError(pubkey_path=pubkey_path)

    if not os.path.isfile(file_path):
        message_display.failure(f"The file {file_path} does not exist.")
        raise exceptions.FileDoesNotExistError(file_path=file_path)

    if not check_url(api_url):
        message_display.failure(f"The url {api_url} is currently not reachable.")
        raise exceptions.ApiNotReachableError(api_url=api_url)

    try:
        upload_id, part_size = start_multipart_upload(
            api_url=api_url, file_id=file_id, pubkey_path=pubkey_path
        )
    except exceptions.NoUploadPossibleError as error:
        message_display.failure(
            f"This user can't start a multipart upload for the file_id '{file_id}'"
        )
        raise error
    except exceptions.UploadNotRegisteredError as error:
        message_display.failure(
            f"The pending upload for file '{file_id}' does not exist."
        )
        raise error
    except exceptions.UserHasNoUploadAccessError as error:
        message_display.failure(
            f"The user is not registered as a Data Submitter for the file with id '{file_id}'."
        )
        raise error
    except exceptions.FileNotRegisteredError as error:
        message_display.failure(f"The file with the id {file_id} is not registered.")
        raise error
    except exceptions.BadResponseCodeError as error:
        message_display.failure(
            "The request was invalid and returnd a wrong HTTP status code."
        )
        raise error
    except exceptions.CantChangeUploadStatusError as error:
        message_display.failure(f"The file with id '{file_id}' was already uploaded.")
        raise error
    except exceptions.RequestFailedError as error:
        message_display.failure("The request has failed.")
        raise error

    try:
        upload_file_parts(
            api_url=api_url,
            upload_id=upload_id,
            part_size=part_size,
            file_path=file_path,
        )
    except exceptions.MaxRetriesReachedError as error:
        message_display.failure(
            "The upload has failed too many times. The upload was aborted."
        )
        raise error

    try:
        patch_multipart_upload(
            api_url=api_url,
            upload_id=upload_id,
            upload_status=UploadStatus.UPLOADED,
        )
    except exceptions.BadResponseCodeError as error:
        message_display.failure(
            f"The request to confirm the upload with id {upload_id} was invalid."
        )
        raise error
    except exceptions.RequestFailedError as error:
        message_display.failure(f"Confirming the upload with id {upload_id} failed.")
        raise error
    message_display.success(f"File with id '{file_id}' has been successfully uploaded.")


def upload_file_parts(
    *,
    api_url: str,
    upload_id: str,
    part_size: int,
    file_path: Path,
) -> None:
    """
    Uploads a file using a specific upload id via uploading all its parts.
    """

    with open(file_path, "rb") as file:
        file_parts = read_file_parts(file, part_size=part_size)
        upload_urls = get_part_upload_urls(api_url=api_url, upload_id=upload_id)

        for part, upload_url in zip(file_parts, upload_urls):
            upload_file_part(presigned_url=upload_url, part=part)


def download(  # pylint: disable=too-many-arguments
    *,
    api_url: str,
    file_id: str,
    output_dir: Path,
    part_size: int,
    message_display: AbstractMessageDisplay,
    max_wait_time: int = MAX_WAIT_TIME,
    pubkey_path: Path,
) -> None:
    """
    Core command to download a file. Can be called by CLI, GUI, etc.
    """

    if not os.path.isdir(output_dir):
        message_display.failure(f"The directory {output_dir} does not exist.")
        raise exceptions.DirectoryDoesNotExistError(output_dir=output_dir)

    if not check_url(api_url):
        message_display.failure(f"The url {api_url} is currently not reachable.")
        raise exceptions.ApiNotReachableError(api_url=api_url)

    download_url, file_size = await_download_url(
        api_url=api_url,
        file_id=file_id,
        max_wait_time=max_wait_time,
        message_display=message_display,
        pubkey_path=pubkey_path,
    )

    # perform the download:

    output_file = os.path.join(output_dir, file_id)
    if os.path.isfile(output_file):
        message_display.failure(f"The file {output_file} already exists.")
        raise exceptions.FileAlreadyExistsError(output_file=output_file)

    try:
        download_parts(
            file_size=file_size,
            download_url=download_url,
            output_file=output_file,
            part_size=part_size,
        )
    except exceptions.MaxRetriesReachedError as error:
        # Remove file, if the download failed.
        os.remove(output_file)
        raise error

    message_display.success(
        f"File with id '{file_id}' has been successfully downloaded."
    )


def download_parts(
    *,
    file_size: int,
    download_url: str,
    output_file: str,
    part_size: int,
) -> None:
    """
    Downloads a file using a specific download_url to download all its parts.
    """

    file_parts = download_file_parts(
        download_url=download_url,
        part_size=part_size,
        total_file_size=file_size,
    )
    with open(output_file, "wb") as file:
        for part in file_parts:
            file.write(part)
