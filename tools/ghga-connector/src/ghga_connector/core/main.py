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

"""Main domain logic."""

from pathlib import Path

import httpx

from ghga_connector.config import get_download_api_url, get_upload_api_url
from ghga_connector.core.downloading.api_calls import DownloadClient
from ghga_connector.core.downloading.batch_processing import FileInfo

from .. import exceptions
from .api_calls import is_service_healthy
from .crypt import Crypt4GHDecryptor
from .downloading.downloader import Downloader
from .file_operations import is_file_encrypted
from .message_display import CLIMessageDisplay
from .uploading.main import run_upload
from .uploading.uploader import Uploader


async def upload_file(  # noqa: PLR0913
    *,
    client: httpx.AsyncClient,
    file_id: str,
    file_path: Path,
    my_public_key_path: Path,
    my_private_key_path: Path,
    part_size: int,
    passphrase: str | None = None,
) -> None:
    """Core command to upload a file. Can be called by CLI, GUI, etc."""
    if not my_public_key_path.is_file():
        raise exceptions.PubKeyFileDoesNotExistError(public_key_path=my_public_key_path)

    if not my_private_key_path.is_file():
        raise exceptions.PrivateKeyFileDoesNotExistError(
            private_key_path=my_private_key_path
        )

    if not file_path.is_file():
        raise exceptions.FileDoesNotExistError(file_path=file_path)

    if is_file_encrypted(file_path):
        raise exceptions.FileAlreadyEncryptedError(file_path=file_path)

    upload_api_url = get_upload_api_url()
    if not is_service_healthy(upload_api_url):
        raise exceptions.ApiNotReachableError(api_url=upload_api_url)

    uploader = Uploader(
        client=client,
        file_id=file_id,
        public_key_path=my_public_key_path,
    )
    try:
        await run_upload(
            file_id=file_id,
            file_path=file_path,
            my_private_key_path=my_private_key_path,
            part_size=part_size,
            passphrase=passphrase,
            uploader=uploader,
        )
    except exceptions.StartUploadError as error:
        CLIMessageDisplay.failure("The request to start a multipart upload has failed.")
        raise error
    except exceptions.CantChangeUploadStatusError as error:
        CLIMessageDisplay.failure(f"The file with id '{file_id}' was already uploaded.")
        raise error
    except exceptions.ConnectionFailedError as error:
        CLIMessageDisplay.failure("The upload failed too many times and was aborted.")
        raise error
    except exceptions.FinalizeUploadError as error:
        CLIMessageDisplay.failure(
            f"Finishing the upload with id '{file_id}' failed.\n{error.cause}"
        )

    CLIMessageDisplay.success(
        f"File with id '{file_id}' has been successfully uploaded."
    )


async def download_file(
    *,
    download_client: DownloadClient,
    part_size: int,
    max_concurrent_downloads: int,
    file_info: FileInfo,
) -> None:
    """Core command to download a file. Can be called by CLI, GUI, etc."""
    file_id = file_info.file_id
    CLIMessageDisplay.display(f"Downloading file with id '{file_id}'...")
    download_api_url = get_download_api_url()
    if not is_service_healthy(download_api_url):
        raise exceptions.ApiNotReachableError(api_url=download_api_url)

    downloader = Downloader(
        download_client=download_client,
        file_id=file_id,
        file_size=file_info.file_size,
        max_concurrent_downloads=max_concurrent_downloads,
    )
    try:
        await downloader.download_file(
            output_path=file_info.path_during_download, part_size=part_size
        )
    except exceptions.GetEnvelopeError as error:
        CLIMessageDisplay.failure(
            f"The request to get an envelope for file '{file_id}' failed."
        )
        raise error
    except exceptions.DownloadError as error:
        CLIMessageDisplay.failure(f"Failed downloading with id '{file_id}'.")
        raise error


def get_work_package_token(max_tries: int) -> list[str]:
    """
    Expect the work package id and access token as a colon separated string
    The user will have to input this manually to avoid it becoming part of the
    command line history.
    """
    for _ in range(max_tries):
        work_package_string = input(
            "Please paste the complete download token "
            + "that you copied from the GHGA data portal: "
        )
        work_package_parts = work_package_string.split(":")
        if not (
            len(work_package_parts) == 2
            and 20 <= len(work_package_parts[0]) < 40
            and 80 <= len(work_package_parts[1]) < 120
        ):
            CLIMessageDisplay.display(
                "Invalid input. Please enter the download token "
                + "you got from the GHGA data portal unaltered."
            )
            continue
        return work_package_parts
    raise exceptions.InvalidWorkPackageToken(tries=max_tries)


def decrypt_file(
    input_file: Path,
    output_file: Path,
    decryption_private_key_path: Path,
    passphrase: str | None,
):
    """Delegate decryption of a file Crypt4GH"""
    decryptor = Crypt4GHDecryptor(
        decryption_key_path=decryption_private_key_path, passphrase=passphrase
    )
    decryptor.decrypt_file(input_path=input_file, output_path=output_file)
