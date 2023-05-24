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

""" CLI-specific wrappers around core functions."""

import os
from pathlib import Path

import crypt4gh.keys
import typer
from ghga_service_commons.utils import crypt

from ghga_connector import core
from ghga_connector.config import Config

CONFIG = Config()  # will be patched for testing


class CLIMessageDisplay(core.AbstractMessageDisplay):
    """
    Command line writer message display implementation,
    using different color based on information type
    """

    def display(self, message: str):
        """
        Write message with default color to stdout
        """
        typer.secho(message, fg=core.MessageColors.DEFAULT)

    def success(self, message: str):
        """
        Write message to stdout representing information about a successful operation
        """
        typer.secho(message, fg=core.MessageColors.SUCCESS)

    def failure(self, message: str):
        """
        Write message to stderr representing information about a failed operation
        """
        typer.secho(message, fg=core.MessageColors.FAILURE, err=True)


cli = typer.Typer()


@cli.command()
def upload(  # noqa C901
    *,
    file_id: str = typer.Option(..., help="The id if the file to upload"),
    file_path: Path = typer.Option(..., help="The path to the file to upload"),
    submitter_pubkey_path: Path = typer.Argument(
        "./key.pub",
        help="The path to a public key from the key pair that was announced in the "
        + "metadata. Defaults to key.pub in the current folder.",
    ),
    submitter_private_key_path: Path = typer.Argument(
        "./key.sec",
        help="The path to a private key from the key pair that will be used to encrypt the "
        + "crypt4gh envelope. Defaults to key in the current folder.",
    ),
):
    """
    Command to upload a file
    """
    core.RequestsSession.configure(CONFIG.max_retries)

    core.upload(
        api_url=CONFIG.upload_api,
        file_id=file_id,
        file_path=file_path,
        message_display=CLIMessageDisplay(),
        server_pubkey=CONFIG.server_pubkey,
        submitter_pubkey_path=submitter_pubkey_path,
        submitter_private_key_path=submitter_private_key_path,
    )


@cli.command()
def download(  # pylint: disable=too-many-arguments
    *,
    output_dir: Path = typer.Option(
        ..., help="The directory to put the downloaded files into."
    ),
    submitter_pubkey_path: Path = typer.Argument(
        "./key.pub",
        help="The path to a public key from the key pair that was announced in the "
        + "metadata. Defaults to key.pub in the current folder.",
    ),
    submitter_private_key_path: Path = typer.Argument(
        "./key.sec",
        help="The path to a private key from the key pair that will be used to decrypt the"
        + "work package access and work order tokens. Defaults to key in the current folder.",
    ),
):
    """
    Command to download files
    """
    core.RequestsSession.configure(CONFIG.max_retries)
    message_display = CLIMessageDisplay()

    if not submitter_pubkey_path.is_file():
        message_display.failure(f"The file {submitter_pubkey_path} does not exist.")
        raise core.exceptions.PubKeyFileDoesNotExistError(
            pubkey_path=submitter_pubkey_path
        )

    if not output_dir.is_dir():
        message_display.failure(f"The directory {output_dir} does not exist.")
        raise core.exceptions.DirectoryDoesNotExistError(output_dir=output_dir)

    submitter_public_key = crypt4gh.keys.get_public_key(filepath=submitter_pubkey_path)
    submitter_private_key = crypt4gh.keys.get_private_key(
        filepath=submitter_private_key_path, callback=None
    )

    # get work package access token and id from user input, will be used in later PR
    work_package_id, work_package_token = core.main.get_wps_token(
        max_tries=3, message_display=message_display
    )
    decrypted_token = crypt.decrypt(data=work_package_token, key=submitter_private_key)

    work_package_accessor = core.WorkPackageAccessor(
        access_token=decrypted_token,
        api_url=CONFIG.wps_api_url,
        dcs_api_url=CONFIG.download_api,
        package_id=work_package_id,
        submitter_private_key=submitter_private_key,
    )
    file_ids_with_extension = work_package_accessor.get_package_files()

    io_handler = core.CliIoHandler()
    staging_parameters = core.StagingParameters(
        api_url=CONFIG.download_api,
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
            core.download(
                api_url=CONFIG.download_api,
                file_id=file_id,
                file_extension=file_ids_with_extension[file_id],
                output_dir=output_dir,
                max_wait_time=CONFIG.max_wait_time,
                part_size=CONFIG.part_size,
                message_display=message_display,
                submitter_public_key=submitter_public_key,
                work_package_accessor=work_package_accessor,
            )
        file_stager.update_staged_files()


@cli.command()
def decrypt(  # noqa: C901
    *,
    input_dir: Path = typer.Option(
        ...,
        help="Path to the directory containing files that should be decrypted using a "
        + "common decryption key.",
    ),
    output_dir: Path = typer.Option(
        None,
        help="Optional path to a directory the decrypted file should be written to. "
        + "Defaults to current working directory.",
    ),
    decryption_private_key_path: Path = typer.Option(
        ...,
        help="Path to the private key that should be used to decrypt the file.",
    ),
):
    """Command to decrypt a downloaded file"""

    message_display = CLIMessageDisplay()

    if not input_dir.is_dir():
        message_display.failure(
            f"Input directory {input_dir} does not exist or is not a directory."
        )

    if not output_dir:
        output_dir = Path(os.getcwd())

    if output_dir.exists() and not output_dir.is_dir():
        message_display.failure(
            f"Output directory location {input_dir} exists, but is not a directory."
        )

    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    errors = {}
    skipped_files = []
    for input_file in input_dir.iterdir():
        if not input_file.is_file() or not input_file.suffix == ".c4gh":
            skipped_files.append((str(input_file)))
            continue

        # strip the .c4gh extension for the output file
        output_file = output_dir / input_file.with_suffix("")

        if output_file.exists():
            errors[
                str(input_file)
            ] = f"File already exists at {output_file}, will not overwrite."
            continue

        try:
            core.decrypt_file(
                input_file=input_file,
                output_file=output_file,
                decryption_private_key_path=decryption_private_key_path,
            )
        except ValueError as error:
            errors[
                str(input_file)
            ] = f"Could not decrypt the provided file with the given key.\nError: {str(error)}"
            continue

        message_display.success(
            f"Successfully decrypted file {input_file} to location {output_dir}."
        )

    if skipped_files:
        message_display.display(
            "The following files were skipped as they are not .c4gh files"
        )
        for file in skipped_files:
            message_display.display(f"- {file}")

    if errors:
        message_display.failure("The following files could not be decrypted:")
        for input_path, cause in errors.items():
            message_display.failure(f"- {input_path}:\n\t{cause}")
