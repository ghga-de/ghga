# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from dcs.main import consume_events, run_outbox_cleanup, run_rest_app

cli = typer.Typer()


@cli.command(name="run-rest")
def sync_run_api():
    """Run the HTTP REST API."""
    asyncio.run(run_rest_app())


@cli.command(name="consume-events")
def sync_consume_events(run_forever: bool = True):
    """Run an event consumer listening to the specified topic."""
    asyncio.run(consume_events(run_forever=run_forever))


@cli.command(name="cleanup-outbox")
def sync_run_cleanup():
    """Run outbox cleanup"""
    asyncio.run(run_outbox_cleanup())
