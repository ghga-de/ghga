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

from ghga_connector.config import get_config, set_runtime_config
from ghga_connector.core.client import async_client
from ghga_connector.core.downloading.api_calls import DownloadClient
from ghga_connector.core.downloading.batch_processing import FileStager
from ghga_connector.core.downloading.downloader import (
    Downloader,
    handle_download_errors,
)
from ghga_connector.core.uploading.api_calls import UploadClient
from ghga_connector.core.uploading.batch_processing import upload_files_from_list
from ghga_connector.core.uploading.structs import FileInfoForUpload
from ghga_connector.core.work_package import WorkPackageClient

from .. import exceptions
from . import utils
from .crypt import Crypt4GHDecryptor
from .message_display import CLIMessageDisplay


def parse_file_info_for_upload(file_info: list[str]) -> list[FileInfoForUpload]:
    """Given a list of strings, derive a file alias, path, and size from each item."""
    items: list[FileInfoForUpload] = []
    for i, arg in enumerate(file_info, 1):
        if not arg:
            continue
        if "," in arg:
            alias, path = arg.split(",", 1)
            alias = alias.strip()
            if not path.strip():
                raise RuntimeError(
                    f"No path supplied for alias '{alias}' in arg #{i}. Verify input and"
                    + " ensure that alias and file path are separated only by a comma"
                    + " and no whitespace."
                )
            validated_path = utils.parse_file_upload_path(path)
        else:
            validated_path = utils.parse_file_upload_path(arg)
            alias = validated_path.name
        size = validated_path.stat().st_size
        items.append(FileInfoForUpload(alias=alias, path=validated_path, size=size))

    # Ensure unique aliases and file paths
    for field_name in ["alias", "path"]:
        utils.detect_duplicates([getattr(x, field_name) for x in items], field_name)

    return items


async def async_upload(
    *,
    unparsed_file_info: list[str],
    my_public_key_path: Path,
    my_private_key_path: Path,
    passphrase: str | None = None,
):
    """Upload one or more files asynchronously"""
    parsed_file_info = parse_file_info_for_upload(unparsed_file_info)
    async with async_client() as client, set_runtime_config(client=client):
        await upload_files(
            client=client,
            file_info_list=parsed_file_info,
            my_public_key_path=my_public_key_path,
            my_private_key_path=my_private_key_path,
            passphrase=passphrase,
        )


async def upload_files(
    *,
    client: httpx.AsyncClient,
    file_info_list: list[FileInfoForUpload],
    my_public_key_path: Path,
    my_private_key_path: Path,
    passphrase: str | None = None,
) -> None:
    """Core command to upload one or more files. Can be called by CLI, GUI, etc."""
    my_public_key = utils.get_public_key(my_public_key_path)
    my_private_key = utils.get_private_key(my_private_key_path, passphrase)

    work_package_client = WorkPackageClient(
        client=client, my_private_key=my_private_key, my_public_key=my_public_key
    )
    upload_client = UploadClient(client=client, work_package_client=work_package_client)
    config = get_config()

    CLIMessageDisplay.display(f"Preparing to upload {len(file_info_list)} files")
    await upload_files_from_list(
        upload_client=upload_client,
        file_info_list=file_info_list,
        my_private_key=my_private_key,
        configured_part_size=config.part_size,
        max_concurrent_uploads=config.max_concurrent_uploads,
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

    async with async_client() as client, set_runtime_config(client=client):
        CLIMessageDisplay.display("Retrieving API configuration information...")
        work_package_client = WorkPackageClient(
            client=client,
            my_private_key=my_private_key,
            my_public_key=my_public_key,
        )
        file_ids_with_extension = await work_package_client.get_package_files()
        download_client = DownloadClient(
            client=client, work_package_client=work_package_client
        )
        config = get_config()

        CLIMessageDisplay.display("Preparing files for download...")
        file_stager = FileStager(
            wanted_files=file_ids_with_extension,
            output_dir=output_dir,
            work_package_client=work_package_client,
            download_client=download_client,
            config=config,
        )

        # Use file stager to manage downloads
        async for file_info in file_stager.manage_file_downloads(overwrite):
            file_id = file_info.file_id
            download_client.check_download_api_is_reachable()
            downloader = Downloader(
                download_client=download_client,
                file_id=file_id,
                file_size=file_info.file_size,
                max_concurrent_downloads=config.max_concurrent_downloads,
            )
            CLIMessageDisplay.display(f"Downloading file with id '{file_id}'...")
            with handle_download_errors(file_info):
                await downloader.download_file(
                    output_path=file_info.path_during_download,
                    part_size=config.part_size,
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
