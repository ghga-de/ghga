# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from . import exceptions
from .api_calls import is_service_healthy
from .crypt import Crypt4GHDecryptor
from .downloading.downloader import Downloader
from .file_operations import is_file_encrypted
from .message_display import AbstractMessageDisplay
from .uploading.main import run_upload
from .uploading.uploader import Uploader
from .work_package import WorkPackageAccessor


async def upload_file(  # noqa: PLR0913
    *,
    api_url: str,
    client: httpx.AsyncClient,
    file_id: str,
    file_path: Path,
    message_display: AbstractMessageDisplay,
    server_public_key: str,
    my_public_key_path: Path,
    my_private_key_path: Path,
    part_size: int,
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

    if not is_service_healthy(api_url):
        raise exceptions.ApiNotReachableError(api_url=api_url)

    uploader = Uploader(
        api_url=api_url,
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
            server_public_key=server_public_key,
            uploader=uploader,
        )
    except exceptions.StartUploadError as error:
        message_display.failure("The request to start a multipart upload has failed.")
        raise error
    except exceptions.CantChangeUploadStatusError as error:
        message_display.failure(f"The file with id '{file_id}' was already uploaded.")
        raise error
    except exceptions.ConnectionFailedError as error:
        message_display.failure("The upload failed too many times and was aborted.")
        raise error
    except exceptions.FinalizeUploadError as error:
        message_display.failure(
            f"Finishing the upload with id '{file_id}' failed.\n{error.cause}"
        )

    message_display.success(f"File with id '{file_id}' has been successfully uploaded.")


async def download_file(  # noqa: PLR0913
    *,
    api_url: str,
    client: httpx.AsyncClient,
    output_dir: Path,
    part_size: int,
    max_concurrent_downloads: int,
    message_display: AbstractMessageDisplay,
    max_wait_time: int,
    work_package_accessor: WorkPackageAccessor,
    file_id: str,
    file_extension: str = "",
    overwrite: bool = False,
) -> None:
    """Core command to download a file. Can be called by CLI, GUI, etc."""
    if not is_service_healthy(api_url):
        raise exceptions.ApiNotReachableError(api_url=api_url)

    # construct file name with suffix, if given
    file_name = f"{file_id}"
    if file_extension:
        file_name = f"{file_id}{file_extension}"

    # check output file
    output_file = output_dir / f"{file_name}.c4gh"
    if output_file.exists():
        if overwrite:
            message_display.display(
                f"A file with name '{output_file}' already exists and will be overwritten."
            )
        else:
            message_display.failure(
                f"A file with name '{output_file}' already exists. Skipping."
            )
        return

    # with_suffix() might overwrite existing suffixes, do this instead
    output_file_ongoing = output_file.parent / (output_file.name + ".part")
    if output_file_ongoing.exists():
        output_file_ongoing.unlink()

    downloader = Downloader(
        client=client,
        file_id=file_id,
        max_concurrent_downloads=max_concurrent_downloads,
        max_wait_time=max_wait_time,
        message_display=message_display,
        work_package_accessor=work_package_accessor,
    )
    try:
        await downloader.download_file(
            output_path=output_file_ongoing, part_size=part_size
        )
    except exceptions.GetEnvelopeError as error:
        message_display.failure(
            f"The request to get an envelope for file '{file_id}' failed."
        )
        raise error
    except exceptions.DownloadError as error:
        message_display.failure(f"Failed downloading with id '{file_id}'.")
        raise error

    # rename fully downloaded file
    output_file_ongoing.rename(output_file)

    message_display.success(
        f"File with id '{file_id}' has been successfully downloaded."
    )


def get_wps_token(max_tries: int, message_display: AbstractMessageDisplay) -> list[str]:
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
            message_display.display(
                "Invalid input. Please enter the download token "
                + "you got from the GHGA data portal unaltered."
            )
            continue
        return work_package_parts
    raise exceptions.InvalidWorkPackageToken(tries=max_tries)


def decrypt_file(
    input_file: Path, output_file: Path, decryption_private_key_path: Path
):
    """Delegate decryption of a file Crypt4GH"""
    decryptor = Crypt4GHDecryptor(decryption_key_path=decryption_private_key_path)
    decryptor.decrypt_file(input_path=input_file, output_path=output_file)
