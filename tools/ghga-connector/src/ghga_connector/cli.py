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

"""CLI-specific wrappers around core functions."""

import asyncio
import os
import sys
from distutils.util import strtobool
from functools import partial
from pathlib import Path
from types import TracebackType
from typing import Union

import crypt4gh.keys
import typer
from ghga_service_commons.utils import crypt

from ghga_connector import core
from ghga_connector.config import Config

CONFIG = Config()  # type: ignore [call-arg]


class CLIMessageDisplay(core.AbstractMessageDisplay):
    """
    Command line writer message display implementation,
    using different color based on information type
    """

    def display(self, message: str):
        """Write message with default color to stdout"""
        typer.secho(message, fg=core.MessageColors.DEFAULT)

    def success(self, message: str):
        """Write message to stdout representing information about a successful operation"""
        typer.secho(message, fg=core.MessageColors.SUCCESS)

    def failure(self, message: str):
        """Write message to stderr representing information about a failed operation"""
        typer.secho(message, fg=core.MessageColors.FAILURE, err=True)


def exception_hook(
    type_: BaseException,  # pylint: disable=unused-argument
    value: BaseException,
    traceback: Union[TracebackType, None],  # pylint: disable=unused-argument
    message_display: CLIMessageDisplay,
):
    """When debug mode is NOT enabled, gets called to perform final error handling
    before program exits
    """
    message = (
        "An error occurred. Rerun command"
        + " with --debug at the end to see more information."
    )

    if value.args:
        message = value.args[0]

    message_display.failure(message)


cli = typer.Typer(no_args_is_help=True)


def upload(
    *,
    file_id: str = typer.Option(..., help="The id of the file to upload"),
    file_path: Path = typer.Option(..., help="The path to the file to upload"),
    my_public_key_path: Path = typer.Option(
        "./key.pub",
        help="The path to a public key from the key pair that was announced in the "
        + "metadata. Defaults to key.pub in the current folder.",
    ),
    my_private_key_path: Path = typer.Option(
        "./key.sec",
        help="The path to a private key from the key pair that will be used to encrypt the "
        + "crypt4gh envelope. Defaults to key.sec in the current folder.",
    ),
    debug: bool = typer.Option(
        False, help="Set this option in order to view traceback for errors."
    ),
):
    """Command to upload a file"""
    ucs_api_url, server_pubkey, message_display = configure_upload(debug=debug)
    asyncio.run(
        core.upload(
            api_url=ucs_api_url,
            file_id=file_id,
            file_path=file_path,
            message_display=message_display,
            server_public_key=server_pubkey,
            my_public_key_path=my_public_key_path,
            my_private_key_path=my_private_key_path,
        )
    )


def configure_upload(debug: bool = False):
    """Run necessary configuration for file upload"""
    message_display = CLIMessageDisplay()

    if not debug:
        sys.excepthook = partial(exception_hook, message_display=message_display)

    core.HttpxClientState.configure(CONFIG.max_retries)

    wkvs_caller = core.WKVSCaller(CONFIG.wkvs_api_url)
    ucs_api_url = wkvs_caller.get_ucs_api_url()
    server_pubkey = wkvs_caller.get_server_pubkey()

    return ucs_api_url, server_pubkey, message_display


if strtobool(os.getenv("UPLOAD_ENABLED") or "false"):
    cli.command(no_args_is_help=True)(upload)


@cli.command(no_args_is_help=True)
def download(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    output_dir: Path = typer.Option(
        ..., help="The directory to put the downloaded files into."
    ),
    my_public_key_path: Path = typer.Option(
        "./key.pub",
        help="The path to a public key from the Crypt4GH key pair "
        + "that was announced when the download token was created. "
        + "Defaults to key.pub in the current folder.",
    ),
    my_private_key_path: Path = typer.Option(
        "./key.sec",
        help="The path to a private key from the Crypt4GH key pair "
        + "that was announced when the download token was created. "
        + "Defaults to key.sec in the current folder.",
    ),
    debug: bool = typer.Option(
        False, help="Set this option in order to view traceback for errors."
    ),
):
    """Command to download files"""
    core.HttpxClientState.configure(CONFIG.max_retries)
    message_display = CLIMessageDisplay()

    if not debug:
        sys.excepthook = partial(exception_hook, message_display=message_display)

    if not my_public_key_path.is_file():
        raise core.exceptions.PubKeyFileDoesNotExistError(
            pubkey_path=my_public_key_path
        )

    if not output_dir.is_dir():
        raise core.exceptions.DirectoryDoesNotExistError(directory=output_dir)

    my_public_key = crypt4gh.keys.get_public_key(filepath=my_public_key_path)
    my_private_key = crypt4gh.keys.get_private_key(
        filepath=my_private_key_path, callback=None
    )

    # get work package access token and id from user input, will be used in later PR
    work_package_id, work_package_token = core.main.get_wps_token(
        max_tries=3, message_display=message_display
    )
    decrypted_token = crypt.decrypt(data=work_package_token, key=my_private_key)

    message_display.display("Retrieving API configuration information...")
    wkvs_caller = core.WKVSCaller(CONFIG.wkvs_api_url)
    wps_api_url = wkvs_caller.get_wps_api_url()
    dcs_api_url = wkvs_caller.get_dcs_api_url()

    work_package_accessor = core.WorkPackageAccessor(
        access_token=decrypted_token,
        api_url=wps_api_url,
        dcs_api_url=dcs_api_url,
        package_id=work_package_id,
        my_private_key=my_private_key,
        my_public_key=my_public_key,
    )
    file_ids_with_extension = work_package_accessor.get_package_files()

    io_handler = core.CliIoHandler()
    staging_parameters = core.StagingParameters(
        api_url=dcs_api_url,
        file_ids_with_extension=file_ids_with_extension,
        max_wait_time=CONFIG.max_wait_time,
    )

    file_stager = core.FileStager(
        message_display=message_display,
        io_handler=io_handler,
        staging_parameters=staging_parameters,
        work_package_accessor=work_package_accessor,
    )
    file_stager.check_and_stage(output_dir=output_dir)

    while file_stager.file_ids_remain():
        for file_id in file_stager.get_staged():
            message_display.display(f"Downloading file with id '{file_id}'...")
            core.download(
                api_url=dcs_api_url,
                file_id=file_id,
                file_extension=file_ids_with_extension[file_id],
                output_dir=output_dir,
                max_wait_time=CONFIG.max_wait_time,
                part_size=CONFIG.part_size,
                message_display=message_display,
                work_package_accessor=work_package_accessor,
            )
        file_stager.update_staged_files()


@cli.command(no_args_is_help=True)
def decrypt(  # noqa: PLR0912, C901
    *,
    input_dir: Path = typer.Option(
        ...,
        help="Path to the directory containing files that should be decrypted using a "
        + "common decryption key.",
    ),
    output_dir: Path = typer.Option(
        None,
        help="Optional path to a directory that the decrypted file should be written to. "
        + "Defaults to input dir.",
    ),
    my_private_key_path: Path = typer.Option(
        "./key.sec",
        help="The path to a private key from the Crypt4GH key pair "
        + "that was announced when the download token was created. "
        + "Defaults to key.sec in the current folder.",
    ),
    debug: bool = typer.Option(
        False, help="Set this option in order to view traceback for errors."
    ),
):
    """Command to decrypt a downloaded file"""
    message_display = CLIMessageDisplay()

    if not debug:
        sys.excepthook = partial(exception_hook, message_display=message_display)

    if not input_dir.is_dir():
        raise core.exceptions.DirectoryDoesNotExistError(directory=input_dir)

    if not output_dir:
        output_dir = input_dir

    if output_dir.exists() and not output_dir.is_dir():
        raise core.exceptions.OutputPathIsNotDirectory(directory=output_dir)

    if not output_dir.exists():
        message_display.display(f"Creating output directory '{output_dir}'")
        output_dir.mkdir(parents=True)

    errors = {}
    skipped_files = []
    file_count = 0
    for input_file in input_dir.iterdir():
        if not input_file.is_file() or input_file.suffix != ".c4gh":
            skipped_files.append(str(input_file))
            continue

        file_count += 1

        # strip the .c4gh extension for the output file
        output_file = output_dir / input_file.with_suffix("").name

        if output_file.exists():
            errors[
                str(input_file)
            ] = f"File already exists at '{output_file}', will not overwrite."
            continue

        try:
            message_display.display(f"Decrypting file with id '{input_file}'...")
            core.decrypt_file(
                input_file=input_file,
                output_file=output_file,
                decryption_private_key_path=my_private_key_path,
            )
        except ValueError as error:
            errors[
                str(input_file)
            ] = f"Could not decrypt the provided file with the given key.\nError: {str(error)}"
            continue

        message_display.success(
            f"Successfully decrypted file '{input_file}' to location '{output_dir}'."
        )
    if file_count == 0:
        message_display.display(
            f"No files were processed because the directory '{input_dir}' contains no "
            + "applicable files."
        )

    if skipped_files:
        message_display.display(
            "The following files were skipped as they are not .c4gh files:"
        )
        for file in skipped_files:
            message_display.display(f"- {file}")

    if errors:
        message_display.failure("The following files could not be decrypted:")
        for input_path, cause in errors.items():
            message_display.failure(f"- {input_path}:\n\t{cause}")
