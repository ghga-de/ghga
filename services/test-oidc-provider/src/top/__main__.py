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

from ghga_service_commons.api import run_server
from ghga_service_commons.utils.utc_dates import assert_tz_is_utc
from hexkit.log import configure_logging

from .api.main import app  # noqa: F401
from .config import CONFIG, Config


def run(config: Config = CONFIG):
    """Run the service"""
    configure_logging(config=config)
    assert_tz_is_utc()
    print("Starting the test OIDC provider...")
    asyncio.run(run_server(app="top.__main__:app", config=config))


if __name__ == "__main__":
    run()
