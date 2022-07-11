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

from pathlib import Path

import typer

from ghga_connector import core
from ghga_connector.config import Config

config = Config()  # will be patched for testing


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
):
    """
    Command to upload a file
    """

    core.upload(
        api_url=config.upload_api,
        file_id=file_id,
        file_path=file_path,
        max_retries=config.max_retries,
        message_display=CLIMessageDisplay(),
    )


@cli.command()
def download(  # pylint: disable=too-many-arguments
    *,
    file_id: str = typer.Option(..., help="The id if the file to upload"),
    output_dir: Path = typer.Option(
        ..., help="The directory to put the downloaded file"
    ),
):
    """
    Command to download a file
    """

    core.download(
        api_url=config.download_api,
        file_id=file_id,
        output_dir=output_dir,
        max_wait_time=config.max_wait_time,
        part_size=config.part_size,
        max_retries=config.max_retries,
        message_display=CLIMessageDisplay(),
    )
