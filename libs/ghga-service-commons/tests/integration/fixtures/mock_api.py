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
"""Simple set of endpoints designed to test the MockRouter class."""

import json

import httpx

from ghga_service_commons.api.mock_router import MockRouter
from ghga_service_commons.httpyexpect.server.exceptions import HttpException

# Create an instance of the MockRouter with no exception handler
app: MockRouter = MockRouter(exceptions_to_handle=(HttpException,))


# basic way to register an endpoint
@app.get("/hello")
def basic() -> httpx.Response:
    """Define a basic endpoint."""
    return httpx.Response(status_code=200, json={"hello": "world"})


@app.get("/items")
def get_all_items(request: httpx.Request) -> httpx.Response:
    """Endpoint meant to match path with the POST endpoint defined below."""
    if request.method == "POST":
        raise HttpException(
            status_code=500,
            exception_id="badRouting",
            description="A POST request was routed to a GET endpoint",
            data={},
        )
    return httpx.Response(status_code=200, json={"hello": "world"})


@app.get("/items/{item_name}")
def get_item(item_name: str) -> httpx.Response:
    """Endpoint with only one path variable."""
    return httpx.Response(status_code=200, json={"expected": item_name})


@app.get("/items/{item_name}/sizes/{item_size}")
def get_item_and_size(item_name: str, item_size: int) -> httpx.Response:
    """Endpoint with multiple path variables.

    Defined after simpler one with same start to make sure pattern matching works. If
    it did not work, the pattern for the shorter function (/items/item_name) could match
    on the first part of this endpoint's path.

    Also gives a chance to test type-hint interpretation/casting.
    """
    return httpx.Response(status_code=200, json={"expected": [item_name, item_size]})


@app.post("/items")
def add_item(request: httpx.Request) -> httpx.Response:
    """Mock endpoint to test getting data from the request body.

    Expects "detail" in body.
    """
    body: dict[str, dict] = json.loads(request.content)

    if request.method == "GET":
        # should not get here
        raise HttpException(
            status_code=500,
            exception_id="badRouting",
            description="A GET request was routed to a POST endpoint",
            data={},
        )

    if "detail" not in body:
        raise HttpException(
            status_code=422,
            exception_id="noDetail",
            description="No detail found in the request body",
            data={},
        )

    return httpx.Response(status_code=201, json={"expected": body["detail"]})
