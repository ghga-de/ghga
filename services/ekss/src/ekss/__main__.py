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

"""Entrypoint of the package"""

import asyncio

from ghga_service_commons.api import run_server
from hexkit.log import configure_logging

from ekss.adapters.inbound.fastapi_.main import (
    setup_app,
)
from ekss.config import CONFIG, Config

app = setup_app(CONFIG)


def run(config: Config = CONFIG):
    """Run the service"""
    configure_logging(config=CONFIG)
    asyncio.run(run_server(app="ekss.__main__:app", config=config))


if __name__ == "__main__":
    run()
