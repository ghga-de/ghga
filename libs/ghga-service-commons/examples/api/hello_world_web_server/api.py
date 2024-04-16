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

"""Definition of API endpoints."""

from fastapi import Depends, FastAPI

from ghga_service_commons.api import configure_app

from .config import get_config

app = FastAPI()
configure_app(app, config=get_config())


@app.get("/")
async def index(config=Depends(get_config)):
    """Greet the World
    (or whoever was configured in config.greeting).
    """
    return f"Hello {config.greeting}."
