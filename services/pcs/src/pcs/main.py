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

"""In this module object construction and dependency injection is carried out."""

from ghga_service_commons.api import run_server
from hexkit.log import configure_logging

from pcs.config import Config
from pcs.inject import prepare_rest_app


async def run_rest_app():
    """Run the HTTP REST API."""
    config = Config()  # type: ignore
    configure_logging(config=config)

    async with prepare_rest_app(config=config) as app:
        await run_server(app=app, config=config)
