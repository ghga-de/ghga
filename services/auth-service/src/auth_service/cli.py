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

"""Command line interface of the service"""

import asyncio

import typer

from ghga_service_commons.utils.utc_dates import assert_tz_is_utc

cli = typer.Typer()


@cli.callback(invoke_without_command=True)
def require_command(ctx: typer.Context):
    """Run the auth service's REST APIs or its event consumer, or migrate its database."""
    # Deployments that still start the bare executable must fail visibly
    # rather than start a service that skips the migrations.
    if ctx.invoked_subcommand is None:
        typer.echo(
            "auth-service needs a command, it no longer runs without one."
            " Start the service with `auth-service run-rest` or"
            " `auth-service consume-events`, and run"
            " `auth-service migrate-db` before it, for instance in an init container.\n",
            err=True,
        )
        typer.echo(ctx.get_help(), err=True)
        raise typer.Exit(code=2)


# The commands import `main` themselves: importing it builds the module-level
# config, whose validation errors would otherwise hide the message above.


@cli.command(name="run-rest")
def sync_run_api():
    """Run the HTTP REST APIs set in `provide_apis`."""
    from auth_service.main import run_rest_app  # noqa: PLC0415

    assert_tz_is_utc()
    asyncio.run(run_rest_app())


@cli.command(name="consume-events")
def sync_consume_events(run_forever: bool = True):
    """Run an event consumer listening to the configured topic."""
    from auth_service.main import consume_events  # noqa: PLC0415

    asyncio.run(consume_events(run_forever=run_forever))


@cli.command(name="migrate-db")
def sync_migrate_db():
    """Run database migrations."""
    from auth_service.main import migrate_db  # noqa: PLC0415

    asyncio.run(migrate_db())
