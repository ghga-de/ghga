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

"""Contains abstract message display base class"""

import enum

import typer


class MessageColors(str, enum.Enum):
    """
    Define commonly used colors for logging
    For a selection of valid colors see click.termui._ansi_colors:
    https://github.com/pallets/click/blob/c96545f6f4ba0eab99de6ec8b4ceb77c9bdb2528/src/click/termui.py#L30
    """

    DEFAULT = "white"
    SUCCESS = "green"
    FAILURE = "red"


class CLIMessageDisplay:
    """
    Command line writer message display implementation,
    using different color based on information type
    """

    @staticmethod
    def display(message: str):
        """Write message with default color to stdout"""
        typer.secho(message, fg=MessageColors.DEFAULT)

    @staticmethod
    def success(message: str):
        """Write message to stdout representing information about a successful operation"""
        typer.secho(message, fg=MessageColors.SUCCESS)

    @staticmethod
    def failure(message: str):
        """Write message to stderr representing information about a failed operation"""
        typer.secho(message, fg=MessageColors.FAILURE, err=True)
