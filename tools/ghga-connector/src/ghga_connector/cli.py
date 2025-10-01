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
"""CLI-specific wrappers around core functions."""

import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from types import TracebackType

import crypt4gh.keys
import httpx
import typer
from ghga_service_commons.utils import crypt

from ghga_connector.config import CONFIG
from ghga_connector.core import (
    CLIMessageDisplay,
    WorkPackageAccessor,
    async_client,
    exceptions,
)
from ghga_connector.core.api_calls import WKVSCaller
from ghga_connector.core.downloading.batch_processing import FileStager
from ghga_connector.core.main import (
    decrypt_file,
    download_file,
    get_wps_token,
    upload_file,
)


@dataclass
class DownloadParameters:
    """Contains parameters returned by API calls to prepare information needed for download"""

    dcs_api_url: str
    file_ids_with_extension: dict[str, str]
    work_package_accessor: WorkPackageAccessor


@dataclass
class UploadParameters:
    """Contains parameters returned by API calls to prepare information needed for upload"""

    ucs_api_url: str
    server_pubkey: str


@dataclass
class WorkPackageInformation:
    """Wraps decrypted work package token and id to pass to other functions"""

    decrypted_token: str
    package_id: str


def strtobool(value: str) -> bool:
    """Inplace replacement for distutils.utils"""
    return value.lower() in ("y", "yes", "on", "1", "true", "t")


def exception_hook(
    type_: BaseException,
    value: BaseException,
    traceback: TracebackType | None,
):
    """When debug mode is NOT enabled, gets called to perform final error handling
    before program exits
    """
    message = (
        "An error occurred. Rerun command"
        + " with --debug at the end to see more information."
    )

    if value.args:
        message += f"\n{value.args[0]}"

    CLIMessageDisplay.failure(message)


def modify_for_debug(debug: bool):
    """Enable debug logging and configure exception printing if debug=True"""
    if debug:
        # enable debug logging
        logging.basicConfig(level=logging.DEBUG)
        sys.excepthook = partial(exception_hook)


async def retrieve_upload_parameters(client: httpx.AsyncClient) -> UploadParameters:
    """Configure httpx client and retrieve necessary parameters from WKVS"""
    wkvs_caller = WKVSCaller(client=client, wkvs_url=CONFIG.wkvs_api_url)
    ucs_api_url = await wkvs_caller.get_ucs_api_url()
    server_pubkey = await wkvs_caller.get_server_pubkey()

    return UploadParameters(server_pubkey=server_pubkey, ucs_api_url=ucs_api_url)


async def retrieve_download_parameters(
    *,
    client: httpx.AsyncClient,
    my_private_key: bytes,
    my_public_key: bytes,
    work_package_information: WorkPackageInformation,
) -> DownloadParameters:
    """Run necessary API calls to configure file download"""
    wkvs_caller = WKVSCaller(client=client, wkvs_url=CONFIG.wkvs_api_url)
    dcs_api_url = await wkvs_caller.get_dcs_api_url()
    wps_api_url = await wkvs_caller.get_wps_api_url()

    work_package_accessor = WorkPackageAccessor(
        access_token=work_package_information.decrypted_token,
        api_url=wps_api_url,
        client=client,
        dcs_api_url=dcs_api_url,
        package_id=work_package_information.package_id,
        my_private_key=my_private_key,
        my_public_key=my_public_key,
    )
    file_ids_with_extension = await work_package_accessor.get_package_files()

    return DownloadParameters(
        dcs_api_url=dcs_api_url,
        file_ids_with_extension=file_ids_with_extension,
        work_package_accessor=work_package_accessor,
    )


def get_work_package_information(my_private_key: bytes):
    """Fetch a work package id and work package token and decrypt the token"""
    # get work package access token and id from user input
    work_package_id, work_package_token = get_wps_token(max_tries=3)
    decrypted_token = crypt.decrypt(data=work_package_token, key=my_private_key)
    return WorkPackageInformation(
        decrypted_token=decrypted_token, package_id=work_package_id
    )


cli = typer.Typer(no_args_is_help=True)


def upload(  # noqa: PLR0913
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
    passphrase: str | None = typer.Option(
        None,
        help="Passphrase for the encrypted private key. "
        + "Only needs to be provided if the key is actually encrypted.",
    ),
    debug: bool = typer.Option(
        False, help="Set this option in order to view traceback for errors."
    ),
):
    """Wrapper for the async upload function"""
    modify_for_debug(debug)
    asyncio.run(
        async_upload(
            file_id=file_id,
            file_path=file_path,
            my_public_key_path=my_public_key_path,
            my_private_key_path=my_private_key_path,
            passphrase=passphrase,
        )
    )


async def async_upload(
    file_id: str,
    file_path: Path,
    my_public_key_path: Path,
    my_private_key_path: Path,
    passphrase: str | None = None,
):
    """Upload a file asynchronously"""
    async with async_client() as client:
        parameters = await retrieve_upload_parameters(client)
        await upload_file(
            api_url=parameters.ucs_api_url,
            client=client,
            file_id=file_id,
            file_path=file_path,
            server_public_key=parameters.server_pubkey,
            my_public_key_path=my_public_key_path,
            my_private_key_path=my_private_key_path,
            passphrase=passphrase,
            part_size=CONFIG.part_size,
        )


if strtobool(os.getenv("UPLOAD_ENABLED") or "false"):
    cli.command(no_args_is_help=True)(upload)


@cli.command(no_args_is_help=True)
def download(  # noqa: PLR0913
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
    passphrase: str | None = typer.Option(
        None,
        help="Passphrase for the encrypted private key. "
        + "Only needs to be provided if the key is actually encrypted.",
    ),
    debug: bool = typer.Option(
        False, help="Set this option in order to view traceback for errors."
    ),
    overwrite: bool = typer.Option(
        False,
        help="Set to true to overwrite already existing files in the output directory.",
    ),
):
    """Wrapper for the async download function"""
    modify_for_debug(debug)
    asyncio.run(
        async_download(
            output_dir=output_dir,
            my_public_key_path=my_public_key_path,
            my_private_key_path=my_private_key_path,
            passphrase=passphrase,
            overwrite=overwrite,
        )
    )


def get_public_key(my_public_key_path: Path) -> bytes:
    """Get the user's private key from the path supplied"""
    if not my_public_key_path.is_file():
        raise exceptions.PubKeyFileDoesNotExistError(public_key_path=my_public_key_path)

    return crypt4gh.keys.get_public_key(filepath=my_public_key_path)


def get_private_key(my_private_key_path: Path, passphrase: str | None = None) -> bytes:
    """Get the user's private key, using the passphrase if supplied/needed."""
    if passphrase:
        my_private_key = crypt4gh.keys.get_private_key(
            filepath=my_private_key_path, callback=lambda: passphrase
        )
    else:
        my_private_key = crypt4gh.keys.get_private_key(
            filepath=my_private_key_path, callback=None
        )
    return my_private_key


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

    my_public_key = get_public_key(my_public_key_path)
    my_private_key = get_private_key(my_private_key_path, passphrase)

    CLIMessageDisplay.display("\nFetching work package token...")
    work_package_information = get_work_package_information(
        my_private_key=my_private_key
    )

    async with async_client() as client:
        CLIMessageDisplay.display("Retrieving API configuration information...")
        parameters = await retrieve_download_parameters(
            client=client,
            my_private_key=my_private_key,
            my_public_key=my_public_key,
            work_package_information=work_package_information,
        )

        CLIMessageDisplay.display("Preparing files for download...")
        stager = FileStager(
            wanted_file_ids=list(parameters.file_ids_with_extension),
            dcs_api_url=parameters.dcs_api_url,
            output_dir=output_dir,
            work_package_accessor=parameters.work_package_accessor,
            client=client,
            config=CONFIG,
        )
        while not stager.finished:
            staged_files = await stager.get_staged_files()
            for file_id in staged_files:
                CLIMessageDisplay.display(f"Downloading file with id '{file_id}'...")
                await download_file(
                    api_url=parameters.dcs_api_url,
                    client=client,
                    file_id=file_id,
                    file_extension=parameters.file_ids_with_extension[file_id],
                    output_dir=output_dir,
                    max_concurrent_downloads=CONFIG.max_concurrent_downloads,
                    max_wait_time=CONFIG.max_wait_time,
                    part_size=CONFIG.part_size,
                    work_package_accessor=parameters.work_package_accessor,
                    overwrite=overwrite,
                )
            staged_files.clear()


@cli.command(no_args_is_help=True)
def decrypt(  # noqa: PLR0912, C901
    *,
    input_dir: Path = typer.Option(
        ...,
        help="Path to the directory containing files that should be decrypted using a "
        + "common decryption key.",
    ),
    output_dir: Path | None = typer.Option(
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
    passphrase: str | None = typer.Option(
        None,
        help="Passphrase for the encrypted private key. "
        + "Only needs to be provided if the key is actually encrypted.",
    ),
    debug: bool = typer.Option(
        False, help="Set this option in order to view traceback for errors."
    ),
):
    """Command to decrypt a downloaded file"""
    modify_for_debug(debug=debug)

    if not input_dir.is_dir():
        raise exceptions.DirectoryDoesNotExistError(directory=input_dir)

    if not output_dir:
        output_dir = input_dir

    if output_dir.exists() and not output_dir.is_dir():
        raise exceptions.OutputPathIsNotDirectory(directory=output_dir)

    if not output_dir.exists():
        CLIMessageDisplay.display(f"Creating output directory '{output_dir}'")
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
            errors[str(input_file)] = (
                f"File already exists at '{output_file}', will not overwrite."
            )
            continue

        try:
            CLIMessageDisplay.display(f"Decrypting file with id '{input_file}'...")
            decrypt_file(
                input_file=input_file,
                output_file=output_file,
                decryption_private_key_path=my_private_key_path,
                passphrase=passphrase,
            )
        except ValueError as error:
            errors[str(input_file)] = (
                f"Could not decrypt the provided file with the given key.\nError: {str(error)}"
            )
            continue

        CLIMessageDisplay.success(
            f"Successfully decrypted file '{input_file}' to location '{output_dir}'."
        )
    if file_count == 0:
        CLIMessageDisplay.display(
            f"No files were processed because the directory '{input_dir}' contains no "
            + "applicable files."
        )

    if skipped_files:
        CLIMessageDisplay.display(
            "The following files were skipped as they are not .c4gh files:"
        )
        for file in skipped_files:
            CLIMessageDisplay.display(f"- {file}")

    if errors:
        CLIMessageDisplay.failure("The following files could not be decrypted:")
        for input_path, cause in errors.items():
            CLIMessageDisplay.failure(f"- {input_path}:\n\t{cause}")
