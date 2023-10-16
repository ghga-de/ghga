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
"""Handling session initialization for requests"""

from contextlib import asynccontextmanager, contextmanager

import httpx


class HttpxClientState:
    """Helper class to make max_retries user configurable"""

    max_retries: int

    @classmethod
    def configure(cls, max_retries: int):
        """Configure client with exponential backoff retry (using httpx's 0.5 default)"""
        # can't be negative - should we log this?
        cls.max_retries = max(0, max_retries)


@contextmanager
def httpx_client():
    """Yields a context manager httpx client and closes it afterward"""
    transport = httpx.HTTPTransport(retries=HttpxClientState.max_retries)

    with httpx.Client(transport=transport) as client:
        yield client


@asynccontextmanager
async def async_client():
    """Yields a context manager async httpx client and closes it afterward"""
    transport = httpx.AsyncHTTPTransport(retries=HttpxClientState.max_retries)

    async with httpx.AsyncClient(transport=transport) as client:
        yield client
