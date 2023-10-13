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

"""The CLI interface."""

import asyncio
import functools

import typer
from ghga_service_commons.api import run_server

from metldata.combined import get_app
from metldata.config import Config

cli = typer.Typer()


def run_sync(coroutine):
    """A decorator to run a coroutine as a synchronous function."""

    @functools.wraps(coroutine)
    def wrapper(*args, **kwargs):
        return asyncio.run(coroutine(*args, **kwargs))

    return wrapper


@cli.command()
@run_sync
async def run_api() -> None:
    """Run the combined loader and query API."""
    config = Config()  # type: ignore
    app = await get_app(config=config)
    await run_server(app=app, config=config)
