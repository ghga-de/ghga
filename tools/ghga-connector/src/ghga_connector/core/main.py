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

from pathlib import Path
from queue import Empty, Queue

from ghga_connector.core import exceptions
from ghga_connector.core.api_calls import (
    WorkPackageAccessor,
    await_download_url,
    check_url,
    get_download_urls,
    get_file_header_envelope,
)
from ghga_connector.core.file_operations import (
    Crypt4GHDecryptor,
    calc_part_ranges,
    download_file_parts,
    is_file_encrypted,
)
from ghga_connector.core.message_display import AbstractMessageDisplay
from ghga_connector.core.upload import run_upload


async def upload(  # noqa C901, pylint: disable=too-many-statements,too-many-branches
    *,
    api_url: str,
    file_id: str,
    file_path: Path,
    message_display: AbstractMessageDisplay,
    server_public_key: str,
    my_public_key_path: Path,
    my_private_key_path: Path,
) -> None:
    """Core command to upload a file. Can be called by CLI, GUI, etc."""
    if not my_public_key_path.is_file():
        raise exceptions.PubKeyFileDoesNotExistError(pubkey_path=my_public_key_path)

    if not my_private_key_path.is_file():
        raise exceptions.PrivateKeyFileDoesNotExistError(
            private_key_path=my_private_key_path
        )

    if not file_path.is_file():
        raise exceptions.FileDoesNotExistError(file_path=file_path)

    if is_file_encrypted(file_path):
        raise exceptions.FileAlreadyEncryptedError(file_path=file_path)

    if not check_url(api_url):
        raise exceptions.ApiNotReachableError(api_url=api_url)

    await run_upload(
        api_url=api_url,
        file_id=file_id,
        file_path=file_path,
        message_display=message_display,
        private_key_path=my_private_key_path,
        public_key_path=my_public_key_path,
        server_public_key=server_public_key,
    )

    message_display.success(f"File with id '{file_id}' has been successfully uploaded.")


def download(  # noqa: PLR0913
    *,
    api_url: str,
    output_dir: Path,
    part_size: int,
    message_display: AbstractMessageDisplay,
    max_wait_time: int,
    work_package_accessor: WorkPackageAccessor,
    file_id: str,
    file_extension: str = "",
) -> None:
    """Core command to download a file. Can be called by CLI, GUI, etc."""
    if not check_url(api_url):
        raise exceptions.ApiNotReachableError(api_url=api_url)

    # construct file name with suffix, if given
    file_name = f"{file_id}"
    if file_extension:
        file_name = f"{file_id}{file_extension}"

    # check output file
    output_file = output_dir / f"{file_name}.c4gh"
    if output_file.exists():
        raise exceptions.FileAlreadyExistsError(output_file=str(output_file))

    # with_suffix() might overwrite existing suffixes, do this instead
    output_file_ongoing = output_file.parent / (output_file.name + ".part")
    if output_file_ongoing.exists():
        output_file_ongoing.unlink()

    # stage download and get file size
    download_url_tuple = await_download_url(
        file_id=file_id,
        max_wait_time=max_wait_time,
        message_display=message_display,
        work_package_accessor=work_package_accessor,
    )

    # get file header envelope
    try:
        envelope = get_file_header_envelope(
            file_id=file_id,
            work_package_accessor=work_package_accessor,
        )
    except (
        exceptions.FileNotRegisteredError,
        exceptions.EnvelopeNotFoundError,
        exceptions.ExternalApiError,
    ) as error:
        message_display.failure(
            f"The request to get an envelope for file '{file_id}' failed."
        )
        raise error

    # perform the download
    try:
        download_parts(
            envelope=envelope,
            output_file=str(output_file_ongoing),
            file_id=file_id,
            part_size=part_size,
            file_size=download_url_tuple[1],
            work_package_accessor=work_package_accessor,
        )
    except exceptions.ConnectionFailedError as error:
        # Remove file, if the download failed.
        output_file_ongoing.unlink()
        raise error
    except exceptions.NoS3AccessMethodError as error:
        output_file_ongoing.unlink()
        raise error

    # rename fully downloaded file
    if output_file.exists():
        raise exceptions.DownloadFinalizationError(file_path=output_file)
    output_file_ongoing.rename(output_file)

    message_display.success(
        f"File with id '{file_id}' has been successfully downloaded."
    )


def download_parts(  # noqa: PLR0913
    *,
    max_concurrent_downloads: int = 5,
    max_queue_size: int = 10,
    part_size: int,
    file_size: int,
    file_id: str,
    output_file: str,
    envelope: bytes,
    work_package_accessor: WorkPackageAccessor,
):
    """
    Downloads a file from the given URL using multiple threads and saves it to a file.

    :param max_concurrent_downloads: Maximum number of parallel downloads.
    :param max_queue_size: Maximum size of the queue.
    :param part_size: Size of each part to download.
    """
    # Split the file into parts based on the part size
    part_ranges = calc_part_ranges(part_size=part_size, total_file_size=file_size)

    # Create a queue object to store downloaded parts
    queue: Queue = Queue(maxsize=max_queue_size)

    # Get the download urls
    download_urls = get_download_urls(
        file_id=file_id, work_package_accessor=work_package_accessor
    )

    # Download the file parts in parallel
    download_file_parts(
        max_concurrent_downloads=max_concurrent_downloads,
        queue=queue,
        part_ranges=part_ranges,
        download_urls=download_urls,
    )

    # Write the downloaded parts to a file
    with open(output_file, "wb") as file:
        # put envelope in file
        file.write(envelope)
        offset = len(envelope)
        downloaded_size = 0
        while downloaded_size < file_size:
            try:
                start, part = queue.get(block=False)
            except Empty:
                continue
            file.seek(offset + start)
            file.write(part)
            downloaded_size += len(part)
            queue.task_done()


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
