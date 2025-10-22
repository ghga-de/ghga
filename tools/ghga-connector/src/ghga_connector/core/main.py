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

from ghga_connector.config import CONFIG, get_upload_api_url, set_runtime_config
from ghga_connector.core.client import async_client
from ghga_connector.core.downloading.api_calls import DownloadClient
from ghga_connector.core.downloading.batch_processing import FileStager
from ghga_connector.core.downloading.downloader import (
    Downloader,
    handle_download_errors,
)
from ghga_connector.core.work_package import WorkPackageClient

from .. import exceptions
from . import utils
from .api_calls import is_service_healthy
from .crypt import Crypt4GHDecryptor
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


async def async_download(
    *,
    output_dir: Path,
    my_public_key_path: Path,
    my_private_key_path: Path,
    passphrase: str | None = None,
    overwrite: bool = False,
):
    """Download files asynchronously"""
    if not output_dir.is_dir():
        raise exceptions.DirectoryDoesNotExistError(directory=output_dir)

    my_public_key = utils.get_public_key(my_public_key_path)
    my_private_key = utils.get_private_key(my_private_key_path, passphrase)

    CLIMessageDisplay.display("\nFetching work package token...")
    work_package_information = utils.get_work_package_information(
        my_private_key=my_private_key
    )

    async with async_client() as client, set_runtime_config(client=client):
        CLIMessageDisplay.display("Retrieving API configuration information...")
        work_package_client = WorkPackageClient(
            access_token=work_package_information.decrypted_token,
            client=client,
            package_id=work_package_information.package_id,
            my_private_key=my_private_key,
            my_public_key=my_public_key,
        )
        file_ids_with_extension = await work_package_client.get_package_files()
        download_client = DownloadClient(
            client=client, work_package_client=work_package_client
        )

        CLIMessageDisplay.display("Preparing files for download...")
        file_stager = FileStager(
            wanted_files=file_ids_with_extension,
            output_dir=output_dir,
            work_package_client=work_package_client,
            download_client=download_client,
            config=CONFIG,
        )

        # Use file stager to manage downloads
        async for file_info in file_stager.manage_file_downloads(overwrite):
            file_id = file_info.file_id
            download_client.check_download_api_is_reachable()
            downloader = Downloader(
                download_client=download_client,
                file_id=file_id,
                file_size=file_info.file_size,
                max_concurrent_downloads=CONFIG.max_concurrent_downloads,
            )
            CLIMessageDisplay.display(f"Downloading file with id '{file_id}'...")
            with handle_download_errors(file_info):
                await downloader.download_file(
                    output_path=file_info.path_during_download,
                    part_size=CONFIG.part_size,
                )


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
