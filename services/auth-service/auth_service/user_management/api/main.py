# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""
Module containing the main FastAPI router and (optionally) top-level API enpoints.
Additional endpoints might be structured in dedicated modules
(each of them having a sub-router).
"""

from datetime import datetime

from fastapi import FastAPI
from ghga_service_chassis_lib.api import configure_app

from ...config import CONFIG, configure_logging
from ..ports.dao import UserDao
from ..ports.dto import UserCreationDto
from .deps import Depends, get_user_dao

configure_logging()

app = FastAPI()
configure_app(app, config=CONFIG)


@app.get("/", operation_id="greet", summary="Greet the world")
async def index():
    """Greet the World"""
    return "Hello World from the User Management."


@app.post("/create_demo_user", operation_id="demo", summary="Create demo user")
async def demo_create_user(user_dao: UserDao = Depends(get_user_dao)):
    """Create a new user (for demonstration only)"""
    demo_user = UserCreationDto(
        ls_id="demo@ls.org",
        name="Demo User",
        email="demo@example.org",
        registration_date=datetime.now(),
    )
    return await user_dao.insert(demo_user)
