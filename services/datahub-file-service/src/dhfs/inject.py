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

"""Dependency injection and component configuration"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from hexkit.providers.s3 import S3ObjectStorage

from dhfs.adapters.outbound.central import CentralClient
from dhfs.adapters.outbound.http import get_configured_httpx_client
from dhfs.adapters.outbound.s3 import S3Client
from dhfs.config import Config
from dhfs.core.cleaner import S3Cleaner
from dhfs.core.interrogator import Interrogator
from dhfs.ports.outbound.cleaner import S3CleanerPort
from dhfs.ports.outbound.interrogator import InterrogatorPort


@asynccontextmanager
async def prepare_interrogator(*, config: Config) -> AsyncGenerator[InterrogatorPort]:
    """Produces a configured InterrogatorPort-compatible instance"""
    object_storage = S3ObjectStorage(config=config)
    async with get_configured_httpx_client(config=config) as httpx_client:
        s3_client = S3Client(
            config=config, object_storage=object_storage, httpx_client=httpx_client
        )
        central_client = CentralClient(config=config, httpx_client=httpx_client)
        yield Interrogator(
            config=config, central_client=central_client, s3_client=s3_client
        )


@asynccontextmanager
async def prepare_interrogation_bucket_cleaner(
    *, config: Config
) -> AsyncGenerator[S3CleanerPort]:
    """Produces a configured S3CleanerPort-compatible instance"""
    object_storage = S3ObjectStorage(config=config)
    async with get_configured_httpx_client(config=config) as httpx_client:
        s3_client = S3Client(
            config=config, object_storage=object_storage, httpx_client=httpx_client
        )
        central_client = CentralClient(config=config, httpx_client=httpx_client)
        yield S3Cleaner(
            config=config, central_client=central_client, s3_client=s3_client
        )
