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

""" CLI-specific wrappers around core functions."""

import os

import typer

from ghga_connector.core import (
    AbstractMessageDisplay,
    BadResponseCodeError,
    GHGAConnectorException,
    MaxRetriesReached,
    MessageColors,
    NoUploadPossibleError,
    RequestFailedError,
    UploadNotRegisteredError,
    UploadStatus,
    await_download_url,
    check_url,
    download_file_parts,
    get_part_upload_urls,
    patch_multipart_upload,
    read_file_parts,
    start_multipart_upload,
    upload_file_part,
)

DEFAULT_PART_SIZE = 16 * 1024 * 1024


class DirectoryDoesNotExist(RuntimeError, GHGAConnectorException):
    """Thrown, when the specified directory does not exist."""

    def __init__(self, output_dir: str):
        message = f"The directory {output_dir} does not exist."
        super().__init__(message)


class FileAlreadyExistsError(RuntimeError, GHGAConnectorException):
    """Thrown, when the specified file already exists."""

    def __init__(self, output_file: str):
        message = f"The file {output_file} does already exist."
        super().__init__(message)


class ApiNotReachable(RuntimeError, GHGAConnectorException):
    """Thrown, when the api is not reachable."""

    def __init__(self, api_url: str):
        message = f"The url {api_url} is currently not reachable."
        super().__init__(message)


class CLIMessageDisplay(AbstractMessageDisplay):
    """
    Command line writer message display implementation,
    using different color based on information type
    """

    def display(self, message: str):
        """
        Write message with default color to stdout
        """
        typer.secho(message, fg=MessageColors.DEFAULT)

    def success(self, message: str):
        """
        Write message to stdout representing information about a successful operation
        """
        typer.secho(message, fg=MessageColors.SUCCESS)

    def failure(self, message: str):
        """
        Write message to stderr representing information about a failed operation
        """
        typer.secho(message, fg=MessageColors.FAILURE, err=True)


cli = typer.Typer()
message_display: AbstractMessageDisplay = CLIMessageDisplay()


@cli.command()
def upload(  # noqa C901
    api_url: str = typer.Option(..., help="Url to the upload contoller"),
    file_id: str = typer.Option(..., help="The id if the file to upload"),
    file_path: str = typer.Option(..., help="The path to the file to upload"),
):
    """
    Command to upload a file
    """
    if not os.path.isfile(file_path):
        message_display.failure(f"The file {file_path} does not exist.")
        raise typer.Abort()

    if not check_url(api_url):
        message_display.failure(f"The url {api_url} is currently not reachable.")
        raise typer.Abort()

    try:
        upload_id, part_size = start_multipart_upload(api_url=api_url, file_id=file_id)
    except NoUploadPossibleError as error:
        message_display.failure(
            f"This user can't start a multipart upload for the file_id '{file_id}'"
        )
        raise typer.Abort() from error
    except UploadNotRegisteredError as error:
        message_display.failure(
            f"There is already an upload pending for file '{file_id}', which can't be cancelled."
        )
        raise typer.Abort() from error
    except BadResponseCodeError as error:
        message_display.failure(
            "The request was invalid and returnd a wrong HTTP status code."
        )
        raise typer.Abort() from error
    except RequestFailedError as error:
        message_display.failure("The request has failed.")
        raise typer.Abort() from error

    try:
        upload_file_parts(
            api_url=api_url,
            upload_id=upload_id,
            part_size=part_size,
            file_path=file_path,
        )
    except MaxRetriesReached as error:
        message_display.failure(
            "The upload has failed too many times. The upload was aborted."
        )
        raise typer.Abort() from error

    try:
        patch_multipart_upload(
            api_url=api_url,
            upload_id=upload_id,
            upload_status=UploadStatus.UPLOADED,
        )
    except BadResponseCodeError as error:
        message_display.failure(
            f"The request to confirm the upload with id {upload_id} was invalid."
        )
        raise typer.Abort() from error
    except RequestFailedError as error:
        message_display.failure(f"Confirming the upload with id {upload_id} failed.")
        raise typer.Abort() from error
    message_display.success(f"File with id '{file_id}' has been successfully uploaded.")


@cli.command()
def download(  # pylint: disable=too-many-arguments
    api_url: str = typer.Option(..., help="Url to the DRS3"),
    file_id: str = typer.Option(..., help="The id if the file to upload"),
    output_dir: str = typer.Option(
        ..., help="The directory to put the downloaded file"
    ),
    max_wait_time: int = typer.Argument(
        "60",
        help="Maximal time in seconds to wait before quitting without a download. ",
    ),
    part_size: int = typer.Argument(
        DEFAULT_PART_SIZE, help="Part size of the downloaded chunks."
    ),
):
    """
    Command to download a file
    """
    if not os.path.isdir(output_dir):
        raise DirectoryDoesNotExist(output_dir)

    if not check_url(api_url):
        raise ApiNotReachable(api_url)

    download_url, file_size = await_download_url(
        api_url=api_url,
        file_id=file_id,
        max_wait_time=max_wait_time,
        message_display=message_display,
    )

    # perform the download:

    output_file = os.path.join(output_dir, file_id)
    if os.path.isfile(output_file):
        raise FileAlreadyExistsError(output_file)

    try:
        download_parts(
            file_size=file_size,
            download_url=download_url,
            output_file=output_file,
            part_size=part_size,
        )
    except MaxRetriesReached as error:
        # Remove file, if the download failed.
        os.remove(output_file)
        raise error

    message_display.success(
        f"File with id '{file_id}' has been successfully downloaded."
    )


def upload_file_parts(
    api_url: str,
    upload_id: str,
    part_size: int,
    file_path: str,
) -> None:
    """
    Uploads a file using a specific upload id via uploading all its parts.
    """

    with open(file_path, "rb") as file:
        file_parts = read_file_parts(file, part_size=part_size)
        upload_urls = get_part_upload_urls(api_url=api_url, upload_id=upload_id)

        for part, upload_url in zip(file_parts, upload_urls):
            upload_file_part(presigned_url=upload_url, part=part)


def download_parts(
    file_size: int,
    download_url: str,
    output_file: str,
    part_size: int,
) -> None:
    """
    Downloads a file using a specific download_url via uploading all its parts.
    """

    file_parts = download_file_parts(
        download_url=download_url,
        part_size=part_size,
        total_file_size=file_size,
    )
    with open(output_file, "wb") as file:
        for part in file_parts:
            file.write(part)
