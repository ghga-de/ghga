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

import typer

from nos.main import consume_events, migrate_db

cli = typer.Typer()


@cli.callback(invoke_without_command=True)
def require_command(ctx: typer.Context):
    """Run the notification orchestration service or migrate its database."""
    # Deployments that still start the bare executable must fail visibly
    # rather than start a service that skips the migrations.
    if ctx.invoked_subcommand is None:
        typer.echo(
            "nos needs a command, it no longer runs without one."
            " Start the service with `nos consume-events`, and run"
            " `nos migrate-db` before it, for instance in an init container.\n",
            err=True,
        )
        typer.echo(ctx.get_help(), err=True)
        raise typer.Exit(code=2)


@cli.command(name="consume-events")
def sync_consume_events(run_forever: bool = True):
    """Run an event consumer listening to the configured topics."""
    asyncio.run(consume_events(run_forever=run_forever))


@cli.command(name="migrate-db")
def sync_migrate_db():
    """Run database migrations."""
    asyncio.run(migrate_db())
