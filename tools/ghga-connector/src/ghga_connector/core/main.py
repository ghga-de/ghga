# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from ghga_connector.constants import DEFAULT_BATCH_MAX_RETRIES
from ghga_connector.core.client import async_client
from ghga_connector.core.downloading.api_calls import DownloadClient
from ghga_connector.core.downloading.batch_processing import FileStager
from ghga_connector.core.downloading.downloader import (
    Downloader,
    handle_download_errors,
)
from ghga_connector.core.uploading.api_calls import UploadClient
from ghga_connector.core.uploading.batch_processing import (
    load_file_info_from_tsv,
    run_batch_upload,
)
from ghga_connector.core.uploading.structs import CoreFileInfo, FileInfoForUpload
from ghga_connector.core.uploading.ubox_shell import UboxShell
from ghga_connector.core.work_package import WorkPackageClient

from .. import exceptions
from . import utils
from .crypt import Crypt4GHDecryptor
from .message_display import CLIMessageDisplay


async def async_batch_upload(  # noqa: PLR0913
    *,
    tsv: Path,
    my_public_key_path: Path,
    my_private_key_path: Path,
    passphrase: str | None = None,
    max_retries: int = DEFAULT_BATCH_MAX_RETRIES,
    dry_run: bool = False,
    shorten: bool = False,
    overwrite: bool = False,
):
    """Upload a batch of files described by a TSV file asynchronously.

    The TSV is expected to have the file path in the first column and the file alias
    in the second column. Files already present in the upload box are skipped and any
    files that fail to upload are retried up to `max_retries` times. If `dry_run` is
    True, the files that would be uploaded are listed but no uploads are performed. If
    `shorten` is set, long aliases are middle-elided in the output. If `overwrite` is
    True, each uploaded file replaces any existing FileUpload for its alias as long as
    it has not reached the "interrogated" state (re-encrypted).

    A note on file paths: Relative file paths interpreted in the context of the current
    working directory when the batch upload command is executed.
    """
    core_file_info_list = load_file_info_from_tsv(tsv)
    async with async_client() as client, set_runtime_config(client=client):
        await upload_files(
            client=client,
            core_file_info_list=core_file_info_list,
            my_public_key_path=my_public_key_path,
            my_private_key_path=my_private_key_path,
            passphrase=passphrase,
            max_retries=max_retries,
            dry_run=dry_run,
            shorten=shorten,
            overwrite=overwrite,
        )


async def upload_files(  # noqa: PLR0913
    *,
    client: httpx.AsyncClient,
    core_file_info_list: list[CoreFileInfo],
    my_public_key_path: Path,
    my_private_key_path: Path,
    passphrase: str | None = None,
    max_retries: int = DEFAULT_BATCH_MAX_RETRIES,
    dry_run: bool = False,
    shorten: bool = False,
    overwrite: bool = False,
) -> None:
    """Core command to upload a batch of files. Can be called by CLI, GUI, etc.

    Files already present in the upload box are skipped and failures are retried up to
    `max_retries` times. If `dry_run` is True, the files that would be uploaded are
    listed but no uploads are performed. If `shorten` is set, long aliases are
    middle-elided in the output. If `overwrite` is True, each uploaded file replaces any
    existing FileUpload for its alias as long as it has not reached the "interrogated"
    state (re-encrypted).
    """
    my_public_key = utils.get_public_key(my_public_key_path)
    my_private_key = utils.get_private_key(my_private_key_path, passphrase)
    work_package_client = WorkPackageClient(
        client=client, my_private_key=my_private_key, my_public_key=my_public_key
    )
    upload_client = UploadClient(client=client, work_package_client=work_package_client)

    # Add part size to core file info - this enables us to calculate part ranges
    config = get_config()
    full_file_info = [
        FileInfoForUpload(core_file_info=cfi, configured_part_size=config.part_size)
        for cfi in core_file_info_list
    ]

    await run_batch_upload(
        upload_client=upload_client,
        file_info_list=full_file_info,
        my_private_key=my_private_key,
        max_concurrent_uploads=config.max_concurrent_uploads,
        max_retries=max_retries,
        dry_run=dry_run,
        shorten=shorten,
        overwrite=overwrite,
    )


async def async_ubox(
    *,
    my_public_key_path: Path,
    my_private_key_path: Path,
    passphrase: str | None = None,
):
    """Launch an interactive shell for managing a single upload box.

    Prompts for an access token (via the Work Package client), then opens a small
    REPL exposing 'upload', 'ls' and 'rm' commands against the box.
    """
    my_public_key = utils.get_public_key(my_public_key_path)
    my_private_key = utils.get_private_key(my_private_key_path, passphrase)

    async with async_client() as client, set_runtime_config(client=client):
        work_package_client = WorkPackageClient(
            client=client, my_private_key=my_private_key, my_public_key=my_public_key
        )
        upload_client = UploadClient(
            client=client, work_package_client=work_package_client
        )
        shell = UboxShell(upload_client=upload_client, my_private_key=my_private_key)
        await shell.run()


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
