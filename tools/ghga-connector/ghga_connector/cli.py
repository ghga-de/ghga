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

from os import path

import typer

from ghga_connector.core import (
    BadResponseCodeError,
    RequestFailedError,
    check_url,
    download_api_call,
    upload_api_call,
)

cli = typer.Typer()


@cli.command()
def upload(
    api_url: str = typer.Option(..., help="Url to the upload contoller"),
    file_id: str = typer.Option(..., help="The id if the file to upload"),
    file_path: str = typer.Option(..., help="The path to the file to upload"),
):
    """
    Command to upload a file
    """
    if not path.isfile(file_path):
        typer.echo(f"The file {file_path} does not exist.")
        raise typer.Abort()

    if not check_url(api_url):
        typer.echo(f"The url {api_url} is currently not reachable.")
        raise typer.Abort()

    try:
        response_url = upload_api_call(api_url, file_id)
    except BadResponseCodeError as error:
        typer.echo("The request was invalid and returnd a wrong HTTP status code.")
        raise typer.Abort() from error
    except RequestFailedError as error:
        typer.echo("The request has failed.")
        raise typer.Abort() from error

    typer.echo(f"File with id '{file_id}' can be uploaded via {response_url}.")


@cli.command()
def download(
    api_url: str = typer.Option(..., help="Url to the DRS3"),
    file_id: str = typer.Option(..., help="The id if the file to upload"),
    output_dir: str = typer.Option(
        ..., help="The directory to put the downloaded file"
    ),
):
    """
    Command to download a file
    """
    if not path.isdir(output_dir):
        typer.echo(f"The directory {output_dir} does not exist.")
        raise typer.Abort()

    if not check_url(api_url):
        typer.echo(f"The url {api_url} is currently not reachable.")
        raise typer.Abort()

    try:
        response_url = download_api_call(api_url, file_id)
    except BadResponseCodeError as error:
        typer.echo("The request was invalid and returnd a wrong HTTP status code.")
        raise typer.Abort() from error
    except RequestFailedError as error:
        typer.echo("The request has failed.")
        raise typer.Abort() from error

    if response_url is not None:
        typer.echo(f"File with id '{file_id}' can be downloaded via {response_url}.")

    # otherwise do nothing, waiting on a 202 will be implemented later
