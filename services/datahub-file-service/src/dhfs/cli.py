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

"""Entrypoint of the package"""

import asyncio

import typer

from dhfs.main import perform_cleanup, run_interrogator

cli = typer.Typer()


@cli.command(name="interrogate")
def sync_run_api():
    """Run the file interrogation and re-encryption process."""
    asyncio.run(run_interrogator())


@cli.command(name="cleanup")
def sync_run_consume_events():
    """Run the S3 'interrogation' bucket cleanup routine."""
    asyncio.run(perform_cleanup())
