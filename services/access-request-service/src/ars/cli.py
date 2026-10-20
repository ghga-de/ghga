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

"""Entrypoint of the package"""

import asyncio
import sys
from typing import Annotated

import typer

from ars.config import Config
from ars.main import (
    DB_VERSION,
    consume_events,
    migrate_db,
    publish_events,
    run_rest_app,
)
from ghga_service_commons.utils.utc_dates import assert_tz_is_utc
from hexkit.providers.mongodb.migrations import check_db_version

cli = typer.Typer()


@cli.callback(help="")  # an empty help keeps the docstring out of `--help`
def check_version(ctx: typer.Context):
    """Run no command but `migrate-db` unless the database is at `DB_VERSION`."""
    # Click parses a command's own `--help` only after this callback has run
    if ctx.invoked_subcommand == "migrate-db" or "--help" in sys.argv:
        return
    asyncio.run(check_db_version(config=Config(), target_version=DB_VERSION))


@cli.command(name="run-rest")
def sync_run_api():
    """Run the HTTP REST API."""
    assert_tz_is_utc()
    asyncio.run(run_rest_app())


@cli.command(name="consume-events")
def sync_consume_events(run_forever: bool = True):
    """Run an event consumer listening to the configured topic."""
    asyncio.run(consume_events(run_forever=run_forever))


@cli.command(name="publish-events")
def sync_run_publish_events(
    all: Annotated[
        bool, typer.Option(help="Set to (re)publish all events regardless of status")
    ] = False,
):
    """Publish pending events."""
    asyncio.run(publish_events(all=all))


@cli.command(name="migrate-db")
def sync_migrate_db():
    """Run database migrations."""
    asyncio.run(migrate_db())
