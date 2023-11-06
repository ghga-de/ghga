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
#

"""Module hosting the dependency injection framework."""


from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from wkvs.adapters.inbound.fastapi_ import dummies
from wkvs.adapters.inbound.fastapi_.configure import get_configured_app
from wkvs.config import Config


# Please note, a context manager is used here to be identical to the approach taken
# in other microservices.
@asynccontextmanager
async def prepare_rest_app(
    *,
    config: Config,
) -> AsyncGenerator[FastAPI, None]:
    """Construct and initialize an REST API app along with all its dependencies.
    By default, the core dependencies are automatically prepared but you can also
    provide them using the data_repo_override parameter.
    """
    app = get_configured_app(config=config)

    app.dependency_overrides[dummies.config_provider] = lambda: config
    yield app
