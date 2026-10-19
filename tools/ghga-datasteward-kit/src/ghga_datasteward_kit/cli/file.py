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

"""File related CLI"""

from pathlib import Path

import typer

from ghga_datasteward_kit import file_deletion

cli = typer.Typer(no_args_is_help=True)


@cli.command(no_args_is_help=True)
def delete_file(
    file_id: str = typer.Option(
        ...,
        help=(
            "Public ID of the file for which all associated data across file services should be deleted."
        ),
    ),
    config_path: Path = typer.Option(..., help="Path to a config YAML."),
):
    """Call purge controller to remove all data associated with the given file ID from all file services."""
    file_deletion.main(file_id=file_id, config_path=config_path)
