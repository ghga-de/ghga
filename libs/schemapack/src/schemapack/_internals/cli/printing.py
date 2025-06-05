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

"""Utilities for implementing a CLI"""

import rich.console
import rich.panel

EXCEPTION_CONSOLE = rich.console.Console(stderr=True, style="red")
FINAL_SUCCESS_CONSOLE = rich.console.Console(style="green bold", stderr=True)
FINAL_FAILURE_CONSOLE = rich.console.Console(style="red bold", stderr=True)
OUTPUT_CONSOLE = rich.console.Console(soft_wrap=True, markup=False)


def print_exception(exception: Exception, exception_name: str = "Exception"):
    """Print an exception."""
    EXCEPTION_CONSOLE.print(rich.panel.Panel(str(exception), title=exception_name))


def print_final_success(
    message: str,
):
    """Print a final message indicating success."""
    FINAL_SUCCESS_CONSOLE.print(message)


def print_final_failure(
    message: str,
):
    """Print a final message indicating failure."""
    FINAL_FAILURE_CONSOLE.print(message)


def print_output(
    message: str,
):
    """Print primary output of the command."""
    OUTPUT_CONSOLE.print(message)
