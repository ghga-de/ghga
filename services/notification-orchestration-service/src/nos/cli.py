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

import typer

from hexkit.providers.mongodb.migrations import check_db_version
from nos.config import Config
from nos.main import DB_VERSION, consume_events, migrate_db

cli = typer.Typer()


@cli.callback(invoke_without_command=True)
def require_command(ctx: typer.Context):
    """Run the notification orchestration service or migrate its database."""
    # Started without a command, the executable must fail visibly
    # rather than run a service whose migrations may not have run.
    if ctx.invoked_subcommand is None:
        typer.echo(
            "nos needs a command."
            " Start the service with `nos consume-events`, and run"
            " `nos migrate-db` before it, for instance in an init container.\n",
            err=True,
        )
        typer.echo(ctx.get_help(), err=True)
        raise typer.Exit(code=2)
    # Click parses a command's own `--help` only after this callback has run
    if ctx.invoked_subcommand == "migrate-db" or "--help" in sys.argv:
        return
    asyncio.run(check_db_version(config=Config(), target_version=DB_VERSION))


@cli.command(name="consume-events")
def sync_consume_events(run_forever: bool = True):
    """Run an event consumer listening to the configured topics."""
    asyncio.run(consume_events(run_forever=run_forever))


@cli.command(name="migrate-db")
def sync_migrate_db():
    """Run database migrations."""
    asyncio.run(migrate_db())
