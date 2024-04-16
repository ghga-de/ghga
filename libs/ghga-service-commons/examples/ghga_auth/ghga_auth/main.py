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
#

"""Implement global logic for running the application."""

import asyncio

from ghga_auth.config import Config
from ghga_auth.inject import prepare_rest_app
from ghga_service_commons.api import run_server
from ghga_service_commons.utils.utc_dates import assert_tz_is_utc


async def configure_and_run_server():
    """Run the HTTP API."""
    config = Config()  # pyright: ignore
    async with prepare_rest_app(config=config) as app:
        await run_server(app=app, config=config)


def run():
    """Main entry point for running the server."""
    assert_tz_is_utc()
    asyncio.run(configure_and_run_server())
