# Copyright 2021 Universität Tübingen, DKFZ and EMBL
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

from fastapi import Depends, FastAPI

from ..config import get_config
from ..core.greeting import generate_greeting
from ..models import Greeting

app = FastAPI()


@app.get("/", summary="Greet the world")
async def index():
    """Greet the World"""
    return "Hello World."


@app.get(
    "/greet/{name}",
    summary="Greet a person",
    description=(
        "Greet a person by name. You may choose a formal or an informal greeting."
        "The language for the greeting is configured in the backend."
    ),
    response_model=Greeting,
)
async def greet(name: str, isinformal: bool = True, config=Depends(get_config)):
    """Greet a person"""
    return generate_greeting(name=name, language=config.language, isinformal=isinformal)
