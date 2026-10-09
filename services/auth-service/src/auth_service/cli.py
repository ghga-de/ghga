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

from auth_service.main import migrate_db, run

cli = typer.Typer()


@cli.command(name="run-rest")
def sync_run_rest():
    """Run the REST APIs set in `provide_apis`, and the event consumer if `run_consumer`."""
    run()


@cli.command(name="migrate-db")
def sync_migrate_db():
    """Run database migrations."""
    asyncio.run(migrate_db())
